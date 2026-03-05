from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=True,
    )

    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    LOG_LEVEL: str = "INFO"

    VAD_ACTIVATION_THRESHOLD: float = Field(default=0.5, ge=0.0, le=1.0)
    VAD_MIN_SPEECH_DURATION: float = Field(default=0.05, gt=0.0)
    VAD_MIN_SILENCE_DURATION: float = Field(default=0.3, gt=0.0)
