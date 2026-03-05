from __future__ import annotations

import asyncio

import agent as agent_module
import pytest
from livekit.agents import llm


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
    )

    stream = await agent.llm_node(None, [], None)
    items = [item async for item in stream]

    assert items[0] == "Hmm…"
    assert items[1:] == ["LLM", "DONE"]


@pytest.mark.asyncio
async def test_llm_node_injects_voice_guidance_and_labels_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx
        captured["tools"] = tools
        captured["model_settings"] = model_settings
        return "VOICE"

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    original_chat_ctx = llm.ChatContext.empty()
    original_chat_ctx.add_message(role="system", content="BASE_SYSTEM")
    original_chat_ctx.add_message(role="user", content="Voice question")
    original_chat_ctx.add_message(
        role="user",
        content="Text question",
        extra={"mode": "text"},
    )
    original_chat_ctx.add_message(role="assistant", content="Assistant reply")

    agent = agent_module.TwypeAgent(
        mode_voice_guidance="VOICE_GUIDANCE",
        mode_text_guidance="TEXT_GUIDANCE",
        thinking_sounds_enabled=False,
    )

    result = await agent.llm_node(original_chat_ctx, ["tool"], "settings")

    assert result == "VOICE"
    captured_chat_ctx = captured["chat_ctx"]
    assert captured_chat_ctx is not original_chat_ctx
    assert captured_chat_ctx.items[0].role == "system"
    assert captured_chat_ctx.items[0].text_content == "VOICE_GUIDANCE\n\nBASE_SYSTEM"
    assert captured_chat_ctx.items[1].text_content == "[voice] Voice question"
    assert captured_chat_ctx.items[2].text_content == "[text] Text question"
    assert captured_chat_ctx.items[3].text_content == "Assistant reply"
    assert original_chat_ctx.items[0].text_content == "BASE_SYSTEM"
    assert original_chat_ctx.items[1].text_content == "Voice question"
    assert original_chat_ctx.items[2].text_content == "Text question"


@pytest.mark.asyncio
async def test_llm_node_injects_text_guidance_without_fillers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx

        async def gen():
            await asyncio.sleep(0.05)
            yield "LLM"
            yield "DONE"

        return gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    agent = agent_module.TwypeAgent(
        mode_voice_guidance="VOICE_GUIDANCE",
        mode_text_guidance="TEXT_GUIDANCE",
        thinking_sounds_enabled=True,
        thinking_sounds_delay=0.01,
    )
    agent.mode_context.switch_to("text")

    stream = await agent.llm_node(llm.ChatContext.empty(), [], None)
    items = [item async for item in stream]

    assert items == ["LLM", "DONE"]
    assert captured["chat_ctx"].items[0].text_content == "TEXT_GUIDANCE"


def test_message_mode_defaults_to_voice_without_mode_key() -> None:
    message = llm.ChatMessage(role="user", content=["test"])
    agent = agent_module.TwypeAgent()

    assert agent._message_mode(message) == "voice"


def test_annotate_user_message_prefixes_non_string_content() -> None:
    message = llm.ChatMessage(
        role="user",
        content=[],
        extra={"mode": "text"},
    )
    agent = agent_module.TwypeAgent()

    annotated = agent._annotate_user_message(message)

    assert annotated.content == ["[text]"]
    assert message.content == []


@pytest.mark.asyncio
async def test_llm_node_labels_only_recent_user_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx
        return "VOICE"

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    original_chat_ctx = llm.ChatContext.empty()
    for index in range(agent_module.MODE_ANNOTATION_HISTORY_COUNT + 1):
        original_chat_ctx.add_message(role="user", content=f"Question {index}")

    agent = agent_module.TwypeAgent(
        mode_voice_guidance="VOICE_GUIDANCE",
        mode_text_guidance="TEXT_GUIDANCE",
        thinking_sounds_enabled=False,
    )

    result = await agent.llm_node(original_chat_ctx, [], None)

    assert result == "VOICE"
    captured_chat_ctx = captured["chat_ctx"]
    assert captured_chat_ctx.items[1].text_content == "Question 0"
    for index in range(2, agent_module.MODE_ANNOTATION_HISTORY_COUNT + 2):
        assert captured_chat_ctx.items[index].text_content.startswith("[voice] ")


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
    )

    stream = await agent.llm_node(None, [], None)
    items = [item async for item in stream]

    assert items == ["LLM", "DONE"]
