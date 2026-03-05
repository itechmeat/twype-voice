from __future__ import annotations

from fastapi import Request

from src.sessions.settings import LiveKitSettings


def get_livekit_settings(request: Request) -> LiveKitSettings:
    settings = getattr(request.app.state, "livekit_settings", None)
    if settings is None:
        settings = LiveKitSettings()
        request.app.state.livekit_settings = settings
    return settings
