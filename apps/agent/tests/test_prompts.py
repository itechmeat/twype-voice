from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest


def test_require_prompt_layer_returns_trimmed_value() -> None:
    from prompts import require_prompt_layer

    assert (
        require_prompt_layer({"mode_voice_guidance": " Voice "}, "mode_voice_guidance") == "Voice"
    )


def test_require_prompt_layer_raises_for_missing_value() -> None:
    from prompts import require_prompt_layer

    with pytest.raises(RuntimeError, match="mode_voice_guidance"):
        require_prompt_layer({}, "mode_voice_guidance")


def test_build_locale_fallback_chain_prefers_specific_then_default() -> None:
    from prompts import build_locale_fallback_chain

    assert build_locale_fallback_chain("pt-BR") == ("pt-BR", "pt", "en")


def test_build_instructions_with_all_layers() -> None:
    from prompts import PROMPT_LAYER_ORDER, build_instructions

    layers = {key: f"value-{index}" for index, key in enumerate(PROMPT_LAYER_ORDER, start=1)}

    assert build_instructions(layers) == "\n\n".join(layers[key] for key in PROMPT_LAYER_ORDER)


def test_build_instructions_with_partial_layers() -> None:
    from prompts import build_instructions

    layers = {
        "system_prompt": "system",
        "emotion_prompt": "emotion",
        "proactive_prompt": "proactive",
    }

    assert build_instructions(layers) == "system\n\nemotion\n\nproactive"


def test_build_instructions_with_empty_layers() -> None:
    from prompts import build_instructions

    assert build_instructions({}) == ""


@pytest.mark.asyncio
async def test_load_prompt_layers_returns_expected_keys_for_locale_chain() -> None:
    from prompts import (
        MODE_GUIDANCE_KEYS,
        PROMPT_LAYER_ORDER,
        load_prompt_bundle,
        load_prompt_layers,
    )

    class FakeResult:
        def __init__(self, rows: list[dict[str, object]]) -> None:
            self._rows = rows

        def mappings(self) -> FakeResult:
            return self

        def all(self) -> list[dict[str, object]]:
            return self._rows

    class FakeSession:
        def __init__(self) -> None:
            self.params: dict[str, object] | None = None

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def execute(self, statement, params=None):
            self.params = params
            assert "FROM agent_config" in str(statement)
            return FakeResult(
                [
                    {
                        "key": "system_prompt",
                        "locale": "en",
                        "value": "System layer",
                        "version": 3,
                    },
                    {
                        "key": "voice_prompt",
                        "locale": "ru",
                        "value": "Voice layer",
                        "version": 5,
                    },
                    {
                        "key": "mode_voice_guidance",
                        "locale": "en",
                        "value": "Voice guidance",
                        "version": 1,
                    },
                    {
                        "key": "mode_text_guidance",
                        "locale": "ru",
                        "value": "Text guidance",
                        "version": 2,
                    },
                ]
            )

    session = FakeSession()

    class FakeSessionmaker:
        def __call__(self) -> FakeSession:
            return session

    bundle = await load_prompt_bundle(FakeSessionmaker(), "ru")
    layers = await load_prompt_layers(FakeSessionmaker(), "ru")

    assert session.params == {
        "keys": [*PROMPT_LAYER_ORDER, *MODE_GUIDANCE_KEYS],
        "locales": ["ru", "en"],
    }
    assert bundle.requested_locale == "ru"
    assert bundle.locale_chain == ("ru", "en")
    assert bundle.versions == {
        "system_prompt": 3,
        "voice_prompt": 5,
        "mode_voice_guidance": 1,
        "mode_text_guidance": 2,
    }
    assert bundle.resolved_locales == {
        "system_prompt": "en",
        "voice_prompt": "ru",
        "mode_voice_guidance": "en",
        "mode_text_guidance": "ru",
    }
    assert layers == {
        "system_prompt": "System layer",
        "voice_prompt": "Voice layer",
        "mode_voice_guidance": "Voice guidance",
        "mode_text_guidance": "Text guidance",
    }


@pytest.mark.asyncio
async def test_save_config_snapshot_builds_expected_json() -> None:
    from prompts import PromptBundle, save_config_snapshot

    class FakeSession:
        def __init__(self) -> None:
            self.snapshot: dict[str, object] | None = None
            self.commit_calls = 0

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def execute(self, statement, params=None):
            sql = str(statement)
            if "UPDATE sessions" in sql:
                self.snapshot = params["snapshot"]
                assert params["session_id"]
                return None

            raise AssertionError(f"unexpected SQL: {sql}")

        async def commit(self) -> None:
            self.commit_calls += 1

    session = FakeSession()

    class FakeSessionmaker:
        def __call__(self) -> FakeSession:
            return session

    await save_config_snapshot(
        FakeSessionmaker(),
        uuid4(),
        PromptBundle(
            requested_locale="ru-RU",
            locale_chain=("ru-RU", "ru", "en"),
            layers={
                "system_prompt": "System layer",
                "voice_prompt": "Voice layer",
            },
            versions={
                "system_prompt": 3,
                "voice_prompt": 5,
            },
            resolved_locales={
                "system_prompt": "en",
                "voice_prompt": "ru",
            },
        ),
    )

    assert session.commit_calls == 1
    assert session.snapshot is not None
    assert session.snapshot["system_prompt"] == "System layer"
    assert session.snapshot["voice_prompt"] == "Voice layer"
    assert session.snapshot["_version"] == {
        "system_prompt": 3,
        "voice_prompt": 5,
    }
    assert session.snapshot["_meta"]["requested_locale"] == "ru-RU"
    assert session.snapshot["_meta"]["locale_chain"] == ["ru-RU", "ru", "en"]
    assert session.snapshot["_meta"]["resolved_locales"] == {
        "system_prompt": "en",
        "voice_prompt": "ru",
    }
    snapshot_at = session.snapshot["_meta"]["snapshot_at"]
    assert isinstance(snapshot_at, str)
    assert datetime.fromisoformat(snapshot_at)


@pytest.mark.asyncio
async def test_resolve_prompt_locale_prefers_user_preferences() -> None:
    from prompts import resolve_prompt_locale

    class FakeResult:
        def scalar_one_or_none(self) -> dict[str, str]:
            return {"locale": "ru-RU"}

    class FakeSession:
        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def execute(self, statement, params=None):
            assert "FROM sessions" in str(statement)
            return FakeResult()

    class FakeSessionmaker:
        def __call__(self) -> FakeSession:
            return FakeSession()

    locale = await resolve_prompt_locale(
        FakeSessionmaker(),
        uuid4(),
        preferred_locale="en",
    )

    assert locale == "ru-RU"


def test_render_emotional_context_replaces_placeholders() -> None:
    from prompts import render_emotional_context

    template = "Quadrant: {quadrant}, Valence: {valence}, Arousal: {arousal}"
    result = render_emotional_context(
        template,
        {
            "quadrant": "distress",
            "valence": "-0.6",
            "arousal": "0.8",
            "trend_valence": "falling",
            "trend_arousal": "rising",
            "tone_guidance": "Be calm",
        },
    )
    assert result == "Quadrant: distress, Valence: -0.6, Arousal: 0.8"


def test_render_emotional_context_all_placeholders() -> None:
    from prompts import render_emotional_context

    template = "{quadrant} {valence} {arousal} {trend_valence} {trend_arousal} {tone_guidance}"
    vars_ = {
        "quadrant": "excitement",
        "valence": "0.7",
        "arousal": "0.5",
        "trend_valence": "rising",
        "trend_arousal": "stable",
        "tone_guidance": "Enthusiastic",
    }
    result = render_emotional_context(template, vars_)
    assert result == "excitement 0.7 0.5 rising stable Enthusiastic"


def test_render_emotional_context_no_placeholders() -> None:
    from prompts import render_emotional_context

    original = "No emotional placeholders here"
    result = render_emotional_context(original, {"quadrant": "neutral"})
    assert result == original


def test_render_emotional_context_malformed_template() -> None:
    from prompts import render_emotional_context

    malformed = "Bad template {unknown_key} here"
    result = render_emotional_context(malformed, {"quadrant": "neutral"})
    assert result == malformed


def test_render_emotional_context_none_uses_defaults() -> None:
    from prompts import NEUTRAL_EMOTIONAL_DEFAULTS, render_emotional_context

    template = "Q: {quadrant}"
    result = render_emotional_context(template, None)
    assert result == f"Q: {NEUTRAL_EMOTIONAL_DEFAULTS['quadrant']}"


def test_twype_agent_uses_dynamic_instructions(monkeypatch: pytest.MonkeyPatch) -> None:
    import livekit.agents as lk_agents

    captured: dict[str, object] = {}

    def fake_init(self, *args: object, **kwargs: object) -> None:
        captured["instructions"] = kwargs.get("instructions")

    monkeypatch.setattr(lk_agents.Agent, "__init__", fake_init)

    from agent import TwypeAgent

    TwypeAgent(
        instructions="db instructions",
        mode_voice_guidance="voice guidance",
        mode_text_guidance="text guidance",
    )
    assert captured["instructions"] == "db instructions"
