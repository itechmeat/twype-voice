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
from datachannel import publish_transcript
from db import build_engine, build_sessionmaker
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    UserStateChangedEvent,
    WorkerOptions,
    cli,
)
from livekit.agents.voice.room_io import RoomInputOptions
from llm import build_llm
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
    proc.userdata["db_sessionmaker"] = build_sessionmaker(engine)
    configure_transcript_store(proc.userdata["db_sessionmaker"])


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

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    except Exception:
        logger.exception("failed to connect to room, room=%s", ctx.room.name)
        raise

    logger.info("connected to room, room=%s", ctx.room.name)

    last_language = settings.STT_LANGUAGE

    def get_last_language() -> str:
        return last_language

    participant = await ctx.wait_for_participant()
    participant_label = format_participant(participant)
    logger.info("participant joined, room=%s participant=%s", ctx.room.name, participant_label)

    db_session_id = None
    try:
        db_session_id = await resolve_session_id(ctx.room.name)
    except Exception:
        logger.exception("failed to resolve session id, room=%s", ctx.room.name)

    if db_session_id is None:
        logger.error(
            "session not found in db; transcript persistence disabled, room=%s",
            ctx.room.name,
        )

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

    await session.start(
        agent=TwypeAgent(
            thinking_sounds_enabled=settings.THINKING_SOUNDS_ENABLED,
            thinking_sounds_delay=settings.THINKING_SOUNDS_DELAY,
            language_getter=get_last_language,
        ),
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
            if message is None:
                return

            role = str(getattr(message, "role", ""))
            if role != "assistant":
                return

            text = _extract_chat_message_text(message).strip()
            if not text:
                return

            message_id = None
            if db_session_id is not None:
                inserted_id = await save_agent_response(db_session_id, text)
                if inserted_id is not None:
                    message_id = str(inserted_id)

            await publish_transcript(
                ctx.room,
                role="assistant",
                is_final=True,
                text=text,
                language=last_language,
                message_id=message_id,
            )
        except Exception:
            logger.exception("failed to handle assistant message event, room=%s", ctx.room.name)

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

            _llm_error_messages: dict[str, str] = {
                "ru": "Извините, сервис ответа временно недоступен. Попробуйте ещё раз.",
                "en": "Sorry, the response service is temporarily unavailable. Please try again.",
            }
            error_text = _llm_error_messages.get(last_language, _llm_error_messages["en"])

            await publish_transcript(
                ctx.room,
                role="assistant",
                is_final=True,
                text=error_text,
                language=last_language,
            )
        except Exception:
            logger.exception("failed to handle error event, room=%s", ctx.room.name)

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: object) -> None:
        task = asyncio.create_task(handle_transcript_event(ev))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    @session.on("conversation_item_added")
    def on_conversation_item_added(ev: object) -> None:
        task = asyncio.create_task(handle_assistant_message_event(ev))
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
