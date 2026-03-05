from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class LiveKitSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
