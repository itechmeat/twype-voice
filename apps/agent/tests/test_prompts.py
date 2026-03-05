from __future__ import annotations

import pytest


def test_system_prompt_non_empty() -> None:
    from prompts import SYSTEM_PROMPT

    assert SYSTEM_PROMPT.strip()


def test_twype_agent_uses_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    import livekit.agents as lk_agents

    captured: dict[str, object] = {}

    def fake_init(self, *args: object, **kwargs: object) -> None:
        captured["instructions"] = kwargs.get("instructions")

    monkeypatch.setattr(lk_agents.Agent, "__init__", fake_init)

    from agent import TwypeAgent
    from prompts import SYSTEM_PROMPT

    TwypeAgent()
    assert captured["instructions"] == SYSTEM_PROMPT
