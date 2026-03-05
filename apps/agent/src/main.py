import logging
import os
import sys

from agent import TwypeAgent, build_session, build_vad, format_participant
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    UserStateChangedEvent,
    WorkerOptions,
    cli,
)
from settings import AgentSettings

logger = logging.getLogger("twype-agent")


def configure_logging(*, level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def prewarm(proc: JobProcess, settings: AgentSettings) -> None:
    proc.userdata["vad"] = build_vad(settings)


def build_entrypoint(settings: AgentSettings):
    async def entrypoint(ctx: JobContext) -> None:
        logger.info("job accepted, room=%s", ctx.room.name)

        try:
            await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        except Exception:
            logger.exception("failed to connect to room, room=%s", ctx.room.name)
            raise

        logger.info("connected to room, room=%s", ctx.room.name)

        participant = await ctx.wait_for_participant()
        participant_label = format_participant(participant)
        logger.info("participant joined, room=%s participant=%s", ctx.room.name, participant_label)

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(disconnected_participant) -> None:
            if getattr(disconnected_participant, "identity", None) == participant.identity:
                logger.info(
                    "participant left, room=%s participant=%s",
                    ctx.room.name,
                    participant_label,
                )

        session = build_session(settings, vad=ctx.proc.userdata.get("vad"))

        await session.start(
            agent=TwypeAgent(),
            room=ctx.room,
        )

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

    return entrypoint


def main() -> None:
    settings = AgentSettings()

    resolved_level = settings.LOG_LEVEL
    if "dev" in sys.argv[1:] and "LOG_LEVEL" not in os.environ:
        resolved_level = "DEBUG"

    configure_logging(level=resolved_level)
    logger.info("agent starting")

    worker_options = WorkerOptions(
        entrypoint_fnc=build_entrypoint(settings),
        prewarm_fnc=lambda proc: prewarm(proc, settings),
    )

    try:
        cli.run_app(worker_options)
    finally:
        logger.info("agent shutdown")


if __name__ == "__main__":
    main()
