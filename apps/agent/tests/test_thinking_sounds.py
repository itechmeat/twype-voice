from __future__ import annotations

import asyncio

import agent as agent_module
import pytest


@pytest.mark.asyncio
async def test_llm_node_yields_filler_when_first_token_delayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        async def gen():
            await asyncio.sleep(0.05)
            yield "LLM"
            yield "DONE"

        return gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    agent = agent_module.TwypeAgent(
        thinking_sounds_enabled=True,
        thinking_sounds_delay=0.01,
        language_getter=lambda: "ru",
    )

    stream = await agent.llm_node(None, [], None)
    items = [item async for item in stream]

    assert items[0] == "Хм…"
    assert items[1:] == ["LLM", "DONE"]


@pytest.mark.asyncio
async def test_llm_node_does_not_yield_filler_when_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        async def gen():
            await asyncio.sleep(0.001)
            yield "LLM"
            yield "DONE"

        return gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    agent = agent_module.TwypeAgent(
        thinking_sounds_enabled=True,
        thinking_sounds_delay=0.05,
        language_getter=lambda: "en",
    )

    stream = await agent.llm_node(None, [], None)
    items = [item async for item in stream]

    assert items == ["LLM", "DONE"]


@pytest.mark.asyncio
async def test_llm_node_passthrough_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        async def gen():
            await asyncio.sleep(0)
            yield "LLM"
            yield "DONE"

        return gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    agent = agent_module.TwypeAgent(
        thinking_sounds_enabled=False,
        thinking_sounds_delay=0.001,
        language_getter=lambda: "ru",
    )

    stream = await agent.llm_node(None, [], None)
    items = [item async for item in stream]

    assert items == ["LLM", "DONE"]
