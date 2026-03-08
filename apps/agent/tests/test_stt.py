from __future__ import annotations

from typing import Any

from settings import AgentSettings
from stt import TwypeDeepgramSTT, _extract_average_sentiment, build_stt


def test_build_stt_config(monkeypatch, livekit_required_env: None) -> None:
    captured: dict[str, Any] = {}

    def fake_init(self, **kwargs: Any) -> None:
        _ = self
        captured.update(kwargs)

    monkeypatch.setattr(TwypeDeepgramSTT, "__init__", fake_init)

    settings = AgentSettings()
    stt_instance = build_stt(settings)

    assert captured["api_key"] == settings.DEEPGRAM_API_KEY
    assert captured["model"] == settings.STT_MODEL
    assert captured["language"] == settings.STT_LANGUAGE
    assert isinstance(stt_instance, TwypeDeepgramSTT)


def test_extract_average_sentiment_returns_mean_score() -> None:
    score = _extract_average_sentiment(
        {
            "channel": {
                "alternatives": [
                    {
                        "sentiments": [
                            {"sentiment": -0.5},
                            {"sentiment": 0.25},
                            {"sentiment": 0.75},
                        ]
                    }
                ]
            }
        }
    )

    assert score == 0.16666666666666666


def test_extract_average_sentiment_returns_none_without_sentiment_payload() -> None:
    assert (
        _extract_average_sentiment({"channel": {"alternatives": [{"transcript": "Hello"}]}})
        is None
    )
