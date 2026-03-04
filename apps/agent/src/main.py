import logging

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli

logger = logging.getLogger("twype-agent")


async def entrypoint(ctx: JobContext) -> None:
    logger.info("agent started, room=%s", ctx.room.name)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("connected to room %s", ctx.room.name)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
