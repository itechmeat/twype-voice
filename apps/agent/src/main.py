import asyncio
import logging
import os
import sys

from agent import TwypeAgent, build_session, build_vad, format_participant
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
from settings import AgentSettings
from stt import build_stt
from transcript import configure_transcript_store, resolve_session_id, save_transcript

logger = logging.getLogger("twype-agent")


def configure_logging(*, level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def prewarm(proc: JobProcess) -> None:
    settings = _settings
    assert settings is not None

    proc.userdata["vad"] = build_vad(settings)
    proc.userdata["stt"] = build_stt(settings)

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
    assert settings is not None

    logger.info("job accepted, room=%s", ctx.room.name)

    background_tasks: set[asyncio.Task[None]] = set()

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    except Exception:
        logger.exception("failed to connect to room, room=%s", ctx.room.name)
        raise

    logger.info("connected to room, room=%s", ctx.room.name)

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
    )

    await session.start(
        agent=TwypeAgent(),
        room=ctx.room,
    )

    async def handle_transcript_event(ev: object) -> None:
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

            if not is_final:
                await publish_transcript(
                    ctx.room,
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
                is_final=True,
                text=cleaned,
                language=language,
                message_id=message_id,
                sentiment_raw=sentiment_raw,
            )
        except Exception:
            logger.exception("failed to handle transcript event, room=%s", ctx.room.name)

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: object) -> None:
        task = asyncio.create_task(handle_transcript_event(ev))
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
