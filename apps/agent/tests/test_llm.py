from __future__ import annotations

import httpx
import llm as llm_module
import pytest
from settings import AgentSettings


def test_build_llm_passes_litellm_params(
    livekit_required_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeLLM:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(llm_module.openai, "LLM", FakeLLM)

    settings = AgentSettings()
    llm = llm_module.build_llm(settings)

    assert isinstance(llm, FakeLLM)
    assert captured["base_url"] == "http://litellm:4000/v1"
    assert captured["api_key"] == "litellm_master_key"
    assert captured["model"] == "gemini-flash-lite"
    assert captured["temperature"] == 0.7
    assert captured["max_completion_tokens"] == 512

    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 15.0
    assert timeout.read == 15.0
    assert timeout.write == 15.0
    assert timeout.pool == 15.0
