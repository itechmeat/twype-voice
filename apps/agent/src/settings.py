from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=True,
    )

    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    DEEPGRAM_API_KEY: str
    STT_LANGUAGE: str = "multi"
    STT_MODEL: str = "nova-3"

    DATABASE_URL: str

    LITELLM_URL: str
    LITELLM_MASTER_KEY: str

    LLM_MODEL: str = "gemini-flash-lite"
    LLM_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=512, ge=1)

    TTS_PROVIDER: Literal["inworld", "elevenlabs"] = "inworld"

    INWORLD_API_KEY: str | None = None
    TTS_INWORLD_VOICE: str = "Olivia"
    TTS_INWORLD_MODEL: str = "inworld-tts-1.5-mini"
    TTS_SPEAKING_RATE: float = Field(default=1.0, ge=0.5, le=1.5)
    TTS_TEMPERATURE: float = Field(default=1.0, ge=0.0, le=2.0)

    ELEVENLABS_API_KEY: str | None = None
    TTS_ELEVENLABS_VOICE_ID: str = "EXAVITQu4vr4xnSDxMaL"
    TTS_ELEVENLABS_MODEL: str = "eleven_flash_v2_5"

    LOG_LEVEL: str = "INFO"

    VAD_ACTIVATION_THRESHOLD: float = Field(default=0.5, ge=0.0, le=1.0)
    VAD_MIN_SPEECH_DURATION: float = Field(default=0.05, gt=0.0)
    VAD_MIN_SILENCE_DURATION: float = Field(default=0.3, gt=0.0)

    TURN_DETECTION_MODE: Literal["stt", "vad", "manual"] = "stt"
    MIN_ENDPOINTING_DELAY: float = Field(default=0.5, ge=0.0)
    MAX_ENDPOINTING_DELAY: float = Field(default=3.0, gt=0.0)
    PREEMPTIVE_GENERATION: bool = True
    NOISE_CANCELLATION_ENABLED: bool = True
    FALSE_INTERRUPTION_TIMEOUT: float = Field(default=2.0, ge=0.0)
    MIN_INTERRUPTION_DURATION: float = Field(default=0.5, ge=0.0)

    THINKING_SOUNDS_ENABLED: bool = True
    THINKING_SOUNDS_DELAY: float = Field(default=1.5, gt=0.0)

    @model_validator(mode="after")
    def _validate_tts_settings(self) -> AgentSettings:
        if self.TTS_PROVIDER == "inworld" and not self.INWORLD_API_KEY:
            raise ValueError("INWORLD_API_KEY is required when TTS_PROVIDER=inworld")

        if self.TTS_PROVIDER == "elevenlabs" and not self.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is required when TTS_PROVIDER=elevenlabs")

        return self
