import asyncio
import logging
import os
import sys

import httpx
from agent import (
    TwypeAgent,
    build_session,
    build_vad,
    format_participant,
)
from datachannel import (
    publish_chat_response,
    publish_structured_response,
    publish_transcript,
    receive_chat_message,
)
from db import build_engine, build_sessionmaker
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    UserStateChangedEvent,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice.room_io import RoomInputOptions
from llm import build_llm
from prompts import (
    build_instructions,
    load_prompt_bundle,
    require_prompt_layer,
    resolve_prompt_locale,
    save_config_snapshot,
)
from rag import RagEngine
from settings import AgentSettings
from stt import build_stt
from transcript import (
    configure_transcript_store,
    resolve_session_id,
    save_agent_response,
    save_transcript,
)
from tts import build_tts

logger = logging.getLogger("twype-agent")


def configure_logging(*, level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def prewarm(proc: JobProcess) -> None:
    settings = _settings
    if settings is None:
        raise RuntimeError("settings are not configured")

    proc.userdata["vad"] = build_vad(settings)
    proc.userdata["stt"] = build_stt(settings)
    proc.userdata["llm"] = build_llm(settings)
    proc.userdata["tts"] = build_tts(settings, language=settings.STT_LANGUAGE)

    if settings.NOISE_CANCELLATION_ENABLED:
        from livekit.plugins import noise_cancellation

        if not proc.userdata.get("noise_cancellation_loaded"):
            noise_cancellation.load()
            proc.userdata["noise_cancellation_loaded"] = True
        proc.userdata["noise_cancellation"] = noise_cancellation.BVC()

    engine = build_engine(settings)
    proc.userdata["db_engine"] = engine
    sessionmaker = build_sessionmaker(engine)
    proc.userdata["db_sessionmaker"] = sessionmaker
    configure_transcript_store(sessionmaker)

    if settings.RAG_ENABLED:
        proc.userdata["rag_engine"] = RagEngine(settings, sessionmaker)
    else:
        proc.userdata["rag_engine"] = None


def _extract_sentiment_raw(ev: object) -> float | None:
    for attr_name in ("sentiment_raw", "sentiment", "sentiment_score"):
        value = getattr(ev, attr_name, None)
        if isinstance(value, (int, float)):
            return float(value)

    raw = getattr(ev, "raw", None)
    if not isinstance(raw, dict):
        return None

    results = raw.get("results")
    if not isinstance(results, dict):
        return None

    channels = results.get("channels")
    if not isinstance(channels, list) or not channels or not isinstance(channels[0], dict):
        return None

    alternatives = channels[0].get("alternatives")
    if (
        not isinstance(alternatives, list)
        or not alternatives
        or not isinstance(alternatives[0], dict)
    ):
        return None

    sentiments = alternatives[0].get("sentiments")
    if not isinstance(sentiments, list):
        return None

    scores: list[float] = []
    for item in sentiments:
        if not isinstance(item, dict):
            continue
        score = item.get("sentiment")
        if isinstance(score, (int, float)):
            scores.append(float(score))

    return (sum(scores) / len(scores)) if scores else None


_settings: AgentSettings | None = None


async def entrypoint(ctx: JobContext) -> None:
    settings = _settings
    if settings is None:
        raise RuntimeError("settings are not configured")

    logger.info("job accepted, room=%s", ctx.room.name)

    background_tasks: set[asyncio.Task[None]] = set()
    text_reply_lock = asyncio.Lock()

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    except Exception:
        logger.exception("failed to connect to room, room=%s", ctx.room.name)
        raise

    logger.info("connected to room, room=%s", ctx.room.name)

    last_language = (
        settings.STT_LANGUAGE
        if settings.STT_LANGUAGE != "multi"
        else settings.PROMPT_DEFAULT_LOCALE
    )

    participant = await ctx.wait_for_participant()
    participant_label = format_participant(participant)
    logger.info("participant joined, room=%s participant=%s", ctx.room.name, participant_label)

    db_sessionmaker = ctx.proc.userdata.get("db_sessionmaker")
    if db_sessionmaker is None:
        raise RuntimeError("db sessionmaker is not configured")

    db_session_id = await resolve_session_id(ctx.room.name)
    if db_session_id is None:
        raise RuntimeError(f"session not found for room {ctx.room.name}")

    prompt_locale = await resolve_prompt_locale(
        db_sessionmaker,
        db_session_id,
        preferred_locale=last_language,
        default_locale=settings.PROMPT_DEFAULT_LOCALE,
    )
    prompt_bundle = await load_prompt_bundle(
        db_sessionmaker,
        prompt_locale,
        default_locale=settings.PROMPT_DEFAULT_LOCALE,
    )
    instructions = build_instructions(prompt_bundle.layers)
    if not instructions.strip():
        raise RuntimeError("prompt layers are empty")

    mode_voice_guidance = require_prompt_layer(prompt_bundle.layers, "mode_voice_guidance")
    mode_text_guidance = require_prompt_layer(prompt_bundle.layers, "mode_text_guidance")

    logger.info(
        "loaded prompt bundle, requested_locale=%s locale_chain=%s matched_layers=%s",
        prompt_bundle.requested_locale,
        ",".join(prompt_bundle.locale_chain),
        len(prompt_bundle.layers),
    )
    await save_config_snapshot(db_sessionmaker, db_session_id, prompt_bundle)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(disconnected_participant) -> None:
        if getattr(disconnected_participant, "identity", None) == participant.identity:
            logger.info(
                "participant left, room=%s participant=%s",
                ctx.room.name,
                participant_label,
            )

    session = build_session(
        settings,
        vad=ctx.proc.userdata.get("vad"),
        stt=ctx.proc.userdata.get("stt"),
        llm=ctx.proc.userdata.get("llm"),
        tts=ctx.proc.userdata.get("tts"),
    )

    room_input_options = RoomInputOptions(
        noise_cancellation=ctx.proc.userdata.get("noise_cancellation"),
    )

    agent = TwypeAgent(
        instructions=instructions,
        mode_voice_guidance=mode_voice_guidance,
        mode_text_guidance=mode_text_guidance,
        thinking_sounds_enabled=settings.THINKING_SOUNDS_ENABLED,
        thinking_sounds_delay=settings.THINKING_SOUNDS_DELAY,
        default_language=last_language,
        rag_engine=ctx.proc.userdata.get("rag_engine"),
    )
    agent.mode_context.set_language(last_language)
    agent.set_chat_response_publisher(
        lambda chunk: publish_chat_response(
            ctx.room,
            text=chunk,
            is_final=False,
        )
    )
    agent.set_structured_response_publisher(
        lambda result, message_id: publish_structured_response(
            ctx.room,
            items=[
                {
                    "text": item.text,
                    "chunk_ids": [str(chunk_id) for chunk_id in item.chunk_ids],
                }
                for item in result.text_items
            ],
            is_final=True,
            message_id=message_id,
        )
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=room_input_options,
    )

    async def handle_transcript_event(ev: object) -> None:
        nonlocal last_language
        try:
            raw_transcript = getattr(ev, "transcript", None)
            if raw_transcript is None:
                raw_transcript = getattr(ev, "text", "")
            text = str(raw_transcript)
            cleaned = text.strip()
            if not cleaned:
                return

            is_final = bool(getattr(ev, "is_final", False))
            language = str(getattr(ev, "language", settings.STT_LANGUAGE))
            if is_final and language:
                last_language = language
                agent.mode_context.set_language(language)
                agent.mode_context.switch_to("voice")

            if not is_final:
                await publish_transcript(
                    ctx.room,
                    role="user",
                    is_final=False,
                    text=cleaned,
                    language=language,
                )
                return

            sentiment_raw = _extract_sentiment_raw(ev)
            message_id = None

            if db_session_id is not None:
                inserted_id = await save_transcript(
                    db_session_id,
                    cleaned,
                    sentiment_raw,
                    mode=agent.mode_context.current_mode,
                )
                if inserted_id is not None:
                    message_id = str(inserted_id)

            await publish_transcript(
                ctx.room,
                role="user",
                is_final=True,
                text=cleaned,
                language=language,
                message_id=message_id,
                sentiment_raw=sentiment_raw,
            )
        except Exception:
            logger.exception("failed to handle transcript event, room=%s", ctx.room.name)

    def _extract_chat_message_text(message: object) -> str:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return str(content or "")

        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)

        return "".join(chunks)

    async def handle_assistant_message_event(ev: object) -> None:
        try:
            message = getattr(ev, "item", None)
            role = str(getattr(message, "role", "assistant"))
            if message is not None and role != "assistant":
                return

            if message is not None:
                text = _extract_chat_message_text(message).strip()
            else:
                raw_text = getattr(ev, "transcript", None)
                if raw_text is None:
                    raw_text = getattr(ev, "text", "")
                text = str(raw_text).strip()

            if not text:
                return

            completed_response = agent.consume_completed_response()
            response_mode = (
                completed_response.mode
                if completed_response is not None
                else agent.mode_context.current_mode
            )
            dual_layer_result = (
                completed_response.dual_layer_result
                if completed_response is not None
                else agent.last_dual_layer_result
            )
            response_id = (
                completed_response.response_id
                if completed_response is not None
                else agent.current_response_id
            )
            source_ids = (
                [str(chunk_id) for chunk_id in dual_layer_result.all_chunk_ids]
                if dual_layer_result is not None and dual_layer_result.all_chunk_ids
                else None
            )
            message_id = str(response_id) if response_id is not None else None
            if db_session_id is not None:
                inserted_id = await save_agent_response(
                    db_session_id,
                    text,
                    mode=response_mode,
                    source_ids=source_ids,
                    message_id=response_id,
                )
                if inserted_id is not None and message_id is None:
                    message_id = str(inserted_id)

            if response_mode == "text":
                if dual_layer_result is None or not dual_layer_result.text_items:
                    await publish_chat_response(
                        ctx.room,
                        text=text,
                        is_final=True,
                        message_id=message_id,
                    )
            else:
                transcript_text = text
                if dual_layer_result is not None:
                    if not dual_layer_result.voice_text and dual_layer_result.text_items:
                        return
                    if dual_layer_result.voice_text:
                        transcript_text = dual_layer_result.voice_text

                await publish_transcript(
                    ctx.room,
                    role="assistant",
                    is_final=True,
                    text=transcript_text,
                    language=last_language,
                    message_id=message_id,
                )
        except Exception:
            logger.exception("failed to handle assistant message event, room=%s", ctx.room.name)
        finally:
            agent.clear_current_response_id()

    async def handle_error_event(ev: object) -> None:
        try:
            error = getattr(ev, "error", None)
            source = getattr(ev, "source", None)

            error_type = type(error).__name__ if error is not None else ""
            source_type = type(source).__name__ if source is not None else ""

            logger.error(
                "agent error, room=%s error_type=%s source_type=%s error=%r source=%r",
                ctx.room.name,
                error_type,
                source_type,
                error,
                source,
            )

            def is_llm_related(obj: object | None) -> bool:
                if obj is None:
                    return False

                if isinstance(obj, (httpx.TimeoutException, httpx.HTTPError)):
                    return True

                obj_type = type(obj)
                name = str(getattr(obj_type, "__name__", "")).lower()
                module = str(getattr(obj_type, "__module__", "")).lower()
                if any(token in name for token in ("llm", "openai", "litellm")):
                    return True
                if any(token in module for token in ("llm", "openai", "litellm")):
                    return True

                message = str(obj).lower()
                return any(
                    token in message for token in ("timeout", "timed out", "openai", "litellm")
                )

            is_llm_error = is_llm_related(error) or is_llm_related(source)
            if not is_llm_error:
                return

            error_text = "Sorry, the response service is temporarily unavailable. Please try again."

            if agent.mode_context.current_mode == "text":
                await publish_chat_response(
                    ctx.room,
                    text=error_text,
                    is_final=True,
                )
            else:
                await publish_transcript(
                    ctx.room,
                    role="assistant",
                    is_final=True,
                    text=error_text,
                    language=last_language,
                )
        except Exception:
            logger.exception("failed to handle error event, room=%s", ctx.room.name)

    async def handle_data_received_event(data_packet: object) -> None:
        local_participant = getattr(ctx.room, "local_participant", None)
        local_identity = getattr(local_participant, "identity", None)

        try:
            text = receive_chat_message(
                data_packet,
                local_participant_identity=local_identity,
            )
            if text is None:
                return

            agent.mode_context.switch_to("text")
            agent.mode_context.set_language(last_language)

            if db_session_id is not None:
                await save_transcript(
                    db_session_id,
                    text,
                    None,
                    mode=agent.mode_context.current_mode,
                )

            async with text_reply_lock:
                speech_handle = session.generate_reply(
                    user_input=llm.ChatMessage(
                        role="user",
                        content=[text],
                        extra={"mode": agent.mode_context.current_mode},
                    ),
                    input_modality="text",
                )
                await speech_handle
        except Exception:
            logger.exception("failed to handle data packet, room=%s", ctx.room.name)

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: object) -> None:
        task = asyncio.create_task(handle_transcript_event(ev))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    @session.on("agent_speech_committed")
    def on_agent_speech_committed(ev: object) -> None:
        task = asyncio.create_task(handle_assistant_message_event(ev))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    @ctx.room.on("data_received")
    def on_data_received(data_packet: object) -> None:
        task = asyncio.create_task(handle_data_received_event(data_packet))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    @session.on("error")
    def on_error(ev: object) -> None:
        task = asyncio.create_task(handle_error_event(ev))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    @session.on("user_state_changed")
    def on_user_state_changed(ev: UserStateChangedEvent) -> None:
        if ev.new_state == "speaking":
            logger.debug(
                "vad speech_start, room=%s participant=%s",
                ctx.room.name,
                participant_label,
            )
        elif ev.new_state == "listening":
            logger.debug(
                "vad speech_end, room=%s participant=%s",
                ctx.room.name,
                participant_label,
            )
        elif ev.new_state == "away":
            logger.info(
                "participant away, room=%s participant=%s",
                ctx.room.name,
                participant_label,
            )


def main() -> None:
    global _settings
    settings = AgentSettings()
    _settings = settings

    resolved_level = settings.LOG_LEVEL
    if "dev" in sys.argv[1:] and "LOG_LEVEL" not in os.environ:
        resolved_level = "DEBUG"

    configure_logging(level=resolved_level)
    logger.info("agent starting")

    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
    )

    try:
        cli.run_app(worker_options)
    finally:
        logger.info("agent shutdown")


if __name__ == "__main__":
    main()
