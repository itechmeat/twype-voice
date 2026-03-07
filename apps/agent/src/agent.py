from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import uuid
from collections import deque
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from crisis import CrisisDetector, CrisisIntervention
from dual_layer_parser import (
    DualLayerResult,
    DualLayerStreamParser,
    build_dual_layer_result,
    parse_dual_layer_stream,
)
from emotional_analyzer import (
    EmotionalState,
    EmotionalTrendTracker,
    get_tone_guidance,
)
from languages import normalize_language_code
from livekit.agents import Agent, AgentSession, llm
from livekit.agents import tts as livekit_tts
from livekit.plugins import deepgram, silero
from prompts import NEUTRAL_EMOTIONAL_DEFAULTS, render_emotional_context
from rag import RagChunk, RagEngine, format_rag_context
from settings import AgentSettings
from stt import build_stt
from tts import build_tts

logger = logging.getLogger("twype-agent")


_DEFAULT_FILLER_PHRASE = "Hmm…"
MODE_ANNOTATION_HISTORY_COUNT = 6
ModeName = Literal["voice", "text"]


@dataclass(slots=True, frozen=True)
class CompletedResponse:
    response_id: uuid.UUID | None
    mode: ModeName
    dual_layer_result: DualLayerResult
    crisis_intervention: CrisisIntervention | None = None


@dataclass(slots=True)
class PendingUserInput:
    text: str
    message_id: uuid.UUID | None
    language: str | None
    mode: ModeName


@dataclass(slots=True)
class ModeContext:
    current_mode: ModeName = "voice"
    previous_mode: ModeName = "voice"
    current_language: str | None = None
    switched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def switch_to(self, mode: ModeName) -> None:
        if mode == self.current_mode:
            return

        self.previous_mode = self.current_mode
        self.current_mode = mode
        self.switched_at = datetime.now(UTC)

    def set_language(self, language: str | None) -> None:
        normalized = normalize_language_code(language)
        if normalized:
            self.current_language = normalized


def _pick_filler_phrase() -> str:
    return _DEFAULT_FILLER_PHRASE


def _count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def format_participant(participant: Any | None) -> str:
    if participant is None:
        return "<unknown>"

    identity = getattr(participant, "identity", None) or "<no-identity>"
    name = getattr(participant, "name", None) or ""

    if name and name != identity:
        return f"{identity} ({name})"

    return str(identity)


def build_vad(settings: AgentSettings) -> silero.VAD:
    return silero.VAD.load(
        activation_threshold=settings.VAD_ACTIVATION_THRESHOLD,
        min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,
        min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,
    )


def build_session(
    settings: AgentSettings,
    *,
    vad: silero.VAD | None = None,
    stt: deepgram.STT | None = None,
    llm: Any | None = None,
    tts: livekit_tts.TTS | None = None,
    turn_detection: str | None = None,
    min_endpointing_delay: float | None = None,
    max_endpointing_delay: float | None = None,
    preemptive_generation: bool | None = None,
    false_interruption_timeout: float | None = None,
    min_interruption_duration: float | None = None,
) -> AgentSession:
    resolved_vad = vad or build_vad(settings)
    resolved_stt = stt or build_stt(settings)
    resolved_tts = tts or build_tts(settings, language=settings.STT_LANGUAGE)

    resolved_turn_detection = turn_detection or settings.TURN_DETECTION_MODE
    resolved_min_endpointing_delay = (
        settings.MIN_ENDPOINTING_DELAY if min_endpointing_delay is None else min_endpointing_delay
    )
    resolved_max_endpointing_delay = (
        settings.MAX_ENDPOINTING_DELAY if max_endpointing_delay is None else max_endpointing_delay
    )
    resolved_preemptive_generation = (
        settings.PREEMPTIVE_GENERATION if preemptive_generation is None else preemptive_generation
    )
    resolved_false_interruption_timeout = (
        settings.FALSE_INTERRUPTION_TIMEOUT
        if false_interruption_timeout is None
        else false_interruption_timeout
    )
    if resolved_false_interruption_timeout == 0:
        resolved_false_interruption_timeout = None

    resolved_min_interruption_duration = (
        settings.MIN_INTERRUPTION_DURATION
        if min_interruption_duration is None
        else min_interruption_duration
    )

    return AgentSession(
        vad=resolved_vad,
        stt=resolved_stt,
        llm=llm,
        tts=resolved_tts,
        turn_detection=resolved_turn_detection,
        min_endpointing_delay=resolved_min_endpointing_delay,
        max_endpointing_delay=resolved_max_endpointing_delay,
        preemptive_generation=resolved_preemptive_generation,
        false_interruption_timeout=resolved_false_interruption_timeout,
        resume_false_interruption=True,
        min_interruption_duration=resolved_min_interruption_duration,
    )


class TwypeAgent(Agent):
    def __init__(
        self,
        *,
        instructions: str,
        mode_voice_guidance: str,
        mode_text_guidance: str,
        thinking_sounds_enabled: bool = True,
        thinking_sounds_delay: float = 1.5,
        default_language: str = "en",
        rag_engine: RagEngine | None = None,
        crisis_detector: CrisisDetector | None = None,
    ) -> None:
        resolved_instructions = instructions.strip()
        resolved_voice_guidance = mode_voice_guidance.strip()
        resolved_text_guidance = mode_text_guidance.strip()
        if not resolved_instructions:
            raise ValueError("instructions must not be empty")
        if not resolved_voice_guidance:
            raise ValueError("mode_voice_guidance must not be empty")
        if not resolved_text_guidance:
            raise ValueError("mode_text_guidance must not be empty")

        super().__init__(instructions=resolved_instructions)
        self.mode_context = ModeContext()
        self._mode_voice_guidance = resolved_voice_guidance
        self._mode_text_guidance = resolved_text_guidance
        self._thinking_sounds_enabled = thinking_sounds_enabled
        self._thinking_sounds_delay = thinking_sounds_delay
        self._chat_response_publisher: Callable[[str], Awaitable[None]] | None = None
        self._structured_response_publisher: (
            Callable[[DualLayerResult, str | None], Awaitable[None]] | None
        ) = None
        self._default_language = normalize_language_code(default_language) or "en"
        self.rag_engine = rag_engine
        self.crisis_detector = crisis_detector
        self._last_rag_chunks: list[RagChunk] = []
        self._last_dual_layer_result: DualLayerResult | None = None
        self._current_response_id: uuid.UUID | None = None
        self._completed_responses: deque[CompletedResponse] = deque(maxlen=100)
        self.emotional_trend_tracker = EmotionalTrendTracker()
        self.current_emotional_state: EmotionalState | None = None
        self._current_crisis_intervention: CrisisIntervention | None = None
        self._crisis_alert_publisher: Callable[[CrisisIntervention], Awaitable[None]] | None = None
        self._pending_user_input: PendingUserInput | None = None
        self._current_llm_parts: list[str] = []
        self._current_voice_parts: list[str] = []
        self._interrupted_response_text: str | None = None
        self._last_interrupted_token_count = 0

    @property
    def text_mode_active(self) -> bool:
        return self.mode_context.current_mode == "text"

    @property
    def last_dual_layer_result(self) -> DualLayerResult | None:
        return self._last_dual_layer_result

    @property
    def current_response_id(self) -> uuid.UUID | None:
        return self._current_response_id

    @property
    def current_crisis_intervention(self) -> CrisisIntervention | None:
        return self._current_crisis_intervention

    @property
    def current_response_token_count(self) -> int:
        llm_text = "".join(self._current_llm_parts).strip()
        if llm_text:
            return _count_words(llm_text)

        voice_text = "".join(self._current_voice_parts).strip()
        return _count_words(voice_text)

    def consume_completed_response(self) -> CompletedResponse | None:
        if not self._completed_responses:
            return None
        return self._completed_responses.popleft()

    def set_chat_response_publisher(
        self,
        publisher: Callable[[str], Awaitable[None]] | None,
    ) -> None:
        self._chat_response_publisher = publisher

    def set_structured_response_publisher(
        self,
        publisher: Callable[[DualLayerResult, str | None], Awaitable[None]] | None,
    ) -> None:
        self._structured_response_publisher = publisher

    def set_crisis_alert_publisher(
        self,
        publisher: Callable[[CrisisIntervention], Awaitable[None]] | None,
    ) -> None:
        self._crisis_alert_publisher = publisher

    def remember_pending_user_input(
        self,
        *,
        text: str,
        message_id: uuid.UUID | None,
        language: str | None,
        mode: ModeName,
    ) -> None:
        cleaned_text = text.strip()
        if not cleaned_text:
            return

        self._pending_user_input = PendingUserInput(
            text=cleaned_text,
            message_id=message_id,
            language=normalize_language_code(language),
            mode=mode,
        )

    def remember_interrupted_response(self) -> tuple[str, int]:
        voice_text = "".join(self._current_voice_parts).strip()
        llm_text = "".join(self._current_llm_parts).strip()
        snapshot = voice_text or llm_text
        token_count = _count_words(llm_text or snapshot)

        self._interrupted_response_text = snapshot or None
        self._last_interrupted_token_count = token_count
        return snapshot, token_count

    def consume_interrupted_response(self) -> str | None:
        snapshot = self._interrupted_response_text
        self._interrupted_response_text = None
        return snapshot

    def _reset_response_tracking(self) -> None:
        self._current_llm_parts = []
        self._current_voice_parts = []
        self._interrupted_response_text = None
        self._last_interrupted_token_count = 0

    def _track_llm_part(self, chunk: object) -> None:
        if isinstance(chunk, str) and chunk:
            self._current_llm_parts.append(chunk)

    async def _track_voice_stream(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        async for chunk in stream:
            if chunk:
                self._current_voice_parts.append(chunk)
            yield chunk

    async def on_enter(self) -> None:
        participant = getattr(getattr(self.session, "room_io", None), "linked_participant", None)
        logger.info("agent entered session, participant=%s", format_participant(participant))

    def _mode_guidance_text(self) -> str:
        if self.mode_context.current_mode == "text":
            return self._mode_text_guidance
        return self._mode_voice_guidance

    def _message_mode(self, message: llm.ChatMessage) -> ModeName:
        if message.role != "user":
            return "voice"

        extra = message.extra if isinstance(message.extra, dict) else {}
        mode = extra.get("mode")
        if mode in {"voice", "text"}:
            return mode
        return "voice"

    def _annotate_user_message(self, message: llm.ChatMessage) -> llm.ChatMessage:
        annotated = message.model_copy(deep=True)
        if annotated.role != "user":
            return annotated

        prefix = f"[{self._message_mode(annotated)}] "
        updated_content = list(annotated.content)
        for index, item in enumerate(updated_content):
            if isinstance(item, str):
                updated_content[index] = f"{prefix}{item}"
                annotated.content = updated_content
                return annotated

        annotated.content = [prefix.rstrip(), *updated_content]
        return annotated

    def _emotional_vars(self) -> dict[str, str]:
        state = self.current_emotional_state
        if state is None:
            return NEUTRAL_EMOTIONAL_DEFAULTS

        return {
            "quadrant": state.quadrant,
            "valence": str(round(state.valence, 2)),
            "arousal": str(round(state.arousal, 2)),
            "trend_valence": state.trend_valence,
            "trend_arousal": state.trend_arousal,
            "tone_guidance": get_tone_guidance(state.quadrant),
        }

    def _build_mode_aware_chat_ctx(self, chat_ctx: llm.ChatContext | None) -> llm.ChatContext:
        source = chat_ctx.copy() if chat_ctx is not None else llm.ChatContext.empty()
        user_message_indexes = [
            index
            for index, item in enumerate(source.items)
            if isinstance(item, llm.ChatMessage) and item.role == "user"
        ]
        annotated_indexes = set(user_message_indexes[-MODE_ANNOTATION_HISTORY_COUNT:])

        items: list[llm.ChatItem] = []
        merged_into_existing_system = False
        guidance = self._mode_guidance_text()
        emotional_vars = self._emotional_vars()

        for index, item in enumerate(source.items):
            if not isinstance(item, llm.ChatMessage):
                items.append(item)
                continue

            copied_item = item.model_copy(deep=True)

            if copied_item.role == "system" and not merged_into_existing_system:
                updated_content = list(copied_item.content)
                for content_index, content_item in enumerate(updated_content):
                    if isinstance(content_item, str):
                        rendered = render_emotional_context(content_item, emotional_vars)
                        updated_content[content_index] = f"{guidance}\n\n{rendered}"
                        break
                else:
                    updated_content = [guidance, *updated_content]

                copied_item.content = updated_content
                copied_item.extra = {
                    **(copied_item.extra if isinstance(copied_item.extra, dict) else {}),
                    "mode": self.mode_context.current_mode,
                }
                merged_into_existing_system = True
                items.append(copied_item)
                continue

            if copied_item.role == "user" and index in annotated_indexes:
                copied_item = self._annotate_user_message(copied_item)

            items.append(copied_item)

        if not merged_into_existing_system:
            items.insert(
                0,
                llm.ChatMessage(
                    role="system",
                    content=[guidance],
                    extra={"mode": self.mode_context.current_mode},
                ),
            )

        return llm.ChatContext(items=items)

    def _last_user_message(self, chat_ctx: llm.ChatContext | None) -> llm.ChatMessage | None:
        if chat_ctx is None:
            return None

        for item in reversed(chat_ctx.items):
            if isinstance(item, llm.ChatMessage) and item.role == "user":
                return item
        return None

    def _resolve_rag_language(self, message: llm.ChatMessage | None) -> str | None:
        if message is not None and isinstance(message.extra, dict):
            for key in ("language", "locale"):
                value = message.extra.get(key)
                normalized = normalize_language_code(str(value)) if isinstance(value, str) else None
                if normalized:
                    return normalized

        if self.mode_context.current_language:
            return self.mode_context.current_language
        return self._default_language

    async def _inject_rag_context(
        self,
        chat_ctx: llm.ChatContext | None,
        mode_aware_chat_ctx: llm.ChatContext,
    ) -> llm.ChatContext:
        if self._current_crisis_intervention is not None:
            return mode_aware_chat_ctx

        if self.rag_engine is None:
            return mode_aware_chat_ctx

        message = self._last_user_message(chat_ctx)
        if message is None:
            return mode_aware_chat_ctx

        raw_text = message.text_content
        if not raw_text:
            return mode_aware_chat_ctx

        query_text = raw_text.strip()
        if not query_text:
            return mode_aware_chat_ctx

        chunks = await self.rag_engine.search(
            query_text,
            language=self._resolve_rag_language(message),
        )

        self._last_rag_chunks = chunks
        rag_context = format_rag_context(chunks)
        if not rag_context:
            return mode_aware_chat_ctx

        mode_aware_chat_ctx.add_message(
            role="system",
            content=rag_context,
            extra={"rag": True},
        )
        return mode_aware_chat_ctx

    async def llm_node(self, chat_ctx, tools, model_settings):
        self._last_rag_chunks = []
        self._last_dual_layer_result = None
        self._current_response_id = uuid.uuid4()
        self._current_crisis_intervention = None
        self._reset_response_tracking()

        intervention = await self._run_before_llm_cb(chat_ctx)
        if intervention is not None:
            self._current_crisis_intervention = intervention
            if self._crisis_alert_publisher is not None:
                await self._crisis_alert_publisher(intervention)
            mode_aware_chat_ctx = intervention.chat_ctx
        else:
            mode_aware_chat_ctx = self._build_mode_aware_chat_ctx(chat_ctx)
            mode_aware_chat_ctx = await self._inject_rag_context(chat_ctx, mode_aware_chat_ctx)

        if (
            self._current_crisis_intervention is not None
            or not self._thinking_sounds_enabled
            or self.text_mode_active
        ):
            passthrough = super().llm_node(mode_aware_chat_ctx, tools, model_settings)
            if asyncio.iscoroutine(passthrough):
                return await passthrough
            return passthrough

        result = super().llm_node(mode_aware_chat_ctx, tools, model_settings)
        if asyncio.iscoroutine(result):
            result = await result

        if result is None:
            return None

        if isinstance(result, str):
            self._track_llm_part(result)
            return result

        if not hasattr(result, "__aiter__"):
            return result

        async def _gen():
            aiter = result.__aiter__()
            first_task = asyncio.create_task(aiter.__anext__())
            try:
                done, _pending = await asyncio.wait(
                    {first_task},
                    timeout=self._thinking_sounds_delay,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if not done:
                    yield _pick_filler_phrase()

                try:
                    first_item = await first_task
                except StopAsyncIteration:
                    return

                self._track_llm_part(first_item)
                yield first_item

                async for item in aiter:
                    self._track_llm_part(item)
                    yield item
            finally:
                if not first_task.done():
                    first_task.cancel()
                    with contextlib.suppress(Exception):
                        await first_task

        return _gen()

    async def tts_node(self, text: AsyncIterable[str], model_settings):
        if self._current_crisis_intervention is not None:
            return await self._tts_node_crisis(text, model_settings)

        parser = parse_dual_layer_stream(text, rag_chunks=self._last_rag_chunks)
        voice_stream: AsyncIterator[str] = self._track_voice_stream(parser.iter_voice_tokens())

        if not self.text_mode_active:
            try:
                first_voice_chunk = await anext(voice_stream, None)
                if first_voice_chunk is None:
                    await self._close_async_iterable(voice_stream)
                    await self._finalize_dual_layer_result(parser)
                    return None

                result = super().tts_node(
                    self._prepend_chunk(first_voice_chunk, voice_stream),
                    model_settings,
                )

                if asyncio.iscoroutine(result):
                    result = await result

                if result is None:
                    await self._close_async_iterable(voice_stream)
                    await self._finalize_dual_layer_result(parser)
                    return None

                if hasattr(result, "__aiter__"):
                    return self._wrap_tts_output(result, parser, voice_stream)

                await self._close_async_iterable(voice_stream)
                await self._finalize_dual_layer_result(parser)
                return result
            except BaseException:
                await self._close_async_iterable(voice_stream)
                await self._finalize_dual_layer_result(parser)
                raise

        finalized = False
        try:
            async for _chunk in voice_stream:
                pass

            dual_layer_result = await parser.result()
            completed_response = self._record_completed_response(dual_layer_result)
            finalized = True

            if dual_layer_result.text_items and self._structured_response_publisher is not None:
                message_id = (
                    str(completed_response.response_id)
                    if completed_response.response_id is not None
                    else None
                )
                await self._structured_response_publisher(dual_layer_result, message_id)
                return None

            if self._chat_response_publisher is not None and dual_layer_result.voice_text:
                await self._chat_response_publisher(dual_layer_result.voice_text)

            return None
        except BaseException:
            await self._close_async_iterable(voice_stream)
            if not finalized:
                await self._finalize_dual_layer_result(parser)
            raise

    async def _wrap_tts_output(
        self,
        audio_stream: AsyncIterable[Any],
        parser: DualLayerStreamParser,
        voice_stream: AsyncIterator[str],
    ) -> AsyncIterable[Any]:
        try:
            async for frame in audio_stream:
                yield frame
        finally:
            await self._close_async_iterable(voice_stream)
            await self._finalize_dual_layer_result(parser)

    async def _finalize_dual_layer_result(self, parser: DualLayerStreamParser) -> None:
        dual_layer_result = await parser.result()
        completed_response = self._record_completed_response(dual_layer_result)
        if dual_layer_result.text_items and self._structured_response_publisher is not None:
            message_id = (
                str(completed_response.response_id)
                if completed_response.response_id is not None
                else None
            )
            await self._structured_response_publisher(dual_layer_result, message_id)

    async def _close_async_iterable(self, stream: AsyncIterator[str]) -> None:
        aclose = getattr(stream, "aclose", None)
        if callable(aclose):
            await aclose()

    def _record_completed_response(self, dual_layer_result: DualLayerResult) -> CompletedResponse:
        self._last_dual_layer_result = dual_layer_result
        self._interrupted_response_text = None
        self._last_interrupted_token_count = 0
        completed_response = CompletedResponse(
            response_id=self._current_response_id,
            mode=self.mode_context.current_mode,
            dual_layer_result=dual_layer_result,
            crisis_intervention=self._current_crisis_intervention,
        )
        self._completed_responses.append(completed_response)
        return completed_response

    def clear_current_response_id(self) -> None:
        self._current_response_id = None
        self._current_crisis_intervention = None

    async def _prepend_chunk(
        self,
        first_chunk: str,
        stream: AsyncIterable[str],
    ) -> AsyncIterable[str]:
        yield first_chunk
        async for chunk in stream:
            yield chunk

    async def _run_before_llm_cb(
        self,
        chat_ctx: llm.ChatContext | None,
    ) -> CrisisIntervention | None:
        if self.crisis_detector is None or chat_ctx is None:
            return None

        message = self._last_user_message(chat_ctx)
        pending_input = self._consume_pending_user_input(message)
        session_language = pending_input.language if pending_input is not None else None
        user_message_id = pending_input.message_id if pending_input is not None else None

        return await self.crisis_detector.before_llm_cb(
            chat_ctx,
            session_language=session_language,
            high_distress=self.emotional_trend_tracker.high_distress,
            user_message_id=user_message_id,
        )

    def _consume_pending_user_input(
        self,
        message: llm.ChatMessage | None,
    ) -> PendingUserInput | None:
        pending = self._pending_user_input
        if pending is None:
            return None

        if message is None or (message.text_content or "").strip() != pending.text:
            return None

        self._pending_user_input = None
        return pending

    async def _tts_node_crisis(self, text: AsyncIterable[str], model_settings):
        parts: list[str] = []

        async def _stream() -> AsyncIterable[str]:
            async for chunk in text:
                if not chunk:
                    continue
                parts.append(chunk)
                yield chunk

        if not self.text_mode_active:
            try:
                result = super().tts_node(_stream(), model_settings)
                if asyncio.iscoroutine(result):
                    result = await result
            except Exception:
                self._finalize_crisis_result(parts)
                raise

            if result is None:
                self._finalize_crisis_result(parts)
                return None

            if hasattr(result, "__aiter__"):
                return self._wrap_crisis_tts_output(result, parts)

            self._finalize_crisis_result(parts)
            return result

        try:
            async for _chunk in _stream():
                pass
        except Exception:
            self._finalize_crisis_result(parts)
            raise

        full_text = self._finalize_crisis_result(parts)
        if full_text and self._chat_response_publisher is not None:
            await self._chat_response_publisher(full_text)
        return None

    async def _wrap_crisis_tts_output(
        self,
        audio_stream: AsyncIterable[Any],
        parts: list[str],
    ) -> AsyncIterable[Any]:
        try:
            async for frame in audio_stream:
                yield frame
        finally:
            self._finalize_crisis_result(parts)

    def _finalize_crisis_result(self, parts: list[str]) -> str:
        full_text = "".join(parts).strip()
        dual_layer_result = build_dual_layer_result(
            voice_text=full_text,
            text_part="",
            rag_chunks=[],
        )
        self._record_completed_response(dual_layer_result)
        return full_text
