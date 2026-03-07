from __future__ import annotations

from collections.abc import AsyncIterable
from uuid import uuid4

import agent as agent_module
import pytest
from crisis import (
    CrisisClassification,
    CrisisContactInfo,
    CrisisDetector,
    CrisisIntervention,
    CrisisKeywordRule,
)
from livekit.agents import llm


def _detector() -> CrisisDetector:
    return CrisisDetector(
        sessionmaker=lambda: None,  # type: ignore[arg-type]
        base_url="http://litellm:4000",
        api_key="test-key",
        model="gemini-flash-lite",
        http_client=_FakeClient(),  # type: ignore[arg-type]
    )


def _chat_ctx(text: str) -> llm.ChatContext:
    return llm.ChatContext(
        items=[
            llm.ChatMessage(role="system", content=["System"]),
            llm.ChatMessage(role="user", content=[text]),
        ]
    )


def _contact() -> CrisisContactInfo:
    return CrisisContactInfo(
        language="en",
        locale="US",
        contact_type="suicide_hotline",
        name="988 Suicide & Crisis Lifeline",
        phone="988",
        url="https://988lifeline.org/",
        description="Call or text 988",
        priority=1,
    )


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeClient:
    def __init__(self, *, response: _FakeResponse | None = None, error: Exception | None = None):
        self._response = response
        self._error = error

    async def post(self, *args, **kwargs) -> _FakeResponse:
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response

    async def aclose(self) -> None:
        return None


def _intervention(text: str = "Please call 988 right now.") -> CrisisIntervention:
    return CrisisIntervention(
        chat_ctx=llm.ChatContext(
            items=[
                llm.ChatMessage(role="system", content=["Crisis prompt"]),
                llm.ChatMessage(role="user", content=["I want to kill myself"]),
            ]
        ),
        category="suicide",
        confidence=0.92,
        tier=2,
        contacts=[_contact()],
        session_language="en",
        used_high_distress=False,
        user_message_id=uuid4(),
    )


def _stream_text(text: str) -> AsyncIterable[str]:
    async def _gen():
        yield text

    return _gen()


def test_keyword_match_hit_case_insensitive() -> None:
    detector = _detector()
    detector._keyword_cache = {
        "en": [
            CrisisKeywordRule(
                language="en",
                category="suicide",
                pattern="kill myself",
                regex=False,
            )
        ]
    }

    result = detector._find_keyword_match("I might KILL MYSELF tonight", preferred_language="en")

    assert result is not None
    assert result.category == "suicide"


def test_keyword_match_miss_returns_none() -> None:
    detector = _detector()
    detector._keyword_cache = {
        "en": [
            CrisisKeywordRule(
                language="en",
                category="suicide",
                pattern="kill myself",
                regex=False,
            )
        ]
    }

    result = detector._find_keyword_match("Tell me about sleep hygiene", preferred_language="en")

    assert result is None


def test_keyword_match_supports_multi_language() -> None:
    detector = _detector()
    detector._keyword_cache = {
        "ru": [
            CrisisKeywordRule(
                language="ru",
                category="suicide",
                pattern="\u0445\u043e\u0447\u0443 \u0443\u043c\u0435\u0440\u0435\u0442\u044c",
                regex=False,
            )
        ]
    }

    result = detector._find_keyword_match(
        "\u042f \u0445\u043e\u0447\u0443 \u0443\u043c\u0435\u0440\u0435\u0442\u044c "
        "\u043f\u0440\u044f\u043c\u043e \u0441\u0435\u0439\u0447\u0430\u0441",
        preferred_language="en",
    )

    assert result is not None
    assert result.language == "ru"


@pytest.mark.asyncio
async def test_llm_classifier_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = _detector()
    detector._http_client = _FakeClient(
        response=_FakeResponse('{"label":"crisis","confidence":0.91,"category":"suicide"}')
    )

    result = await detector._classify(
        "I want to kill myself",
        language="en",
        keyword_match=None,
        high_distress=False,
    )

    assert result == CrisisClassification("crisis", 0.91, "suicide", False)


@pytest.mark.asyncio
async def test_llm_classifier_reject(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = _detector()
    detector._http_client = _FakeClient(
        response=_FakeResponse('{"label":"not_crisis","confidence":0.12,"category":"suicide"}')
    )

    result = await detector._classify(
        "This homework is killing me",
        language="en",
        keyword_match=None,
        high_distress=False,
    )

    assert result == CrisisClassification("not_crisis", 0.12, "suicide", False)


@pytest.mark.asyncio
async def test_llm_classifier_timeout_is_fail_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = _detector()
    detector._http_client = _FakeClient(error=TimeoutError())

    result = await detector._classify(
        "I want to disappear",
        language="en",
        keyword_match=None,
        high_distress=True,
    )

    assert result.label == "crisis"
    assert result.confidence == 1.0
    assert result.fail_safe is True


def test_invalid_regex_is_ignored() -> None:
    detector = _detector()
    detector._keyword_cache = {
        "en": [
            CrisisKeywordRule(
                language="en",
                category="suicide",
                pattern="[invalid",
                regex=True,
            )
        ]
    }

    result = detector._find_keyword_match("I want to die", preferred_language="en")

    assert result is None


@pytest.mark.asyncio
async def test_ambiguous_confidence_still_triggers_intervention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detector = _detector()
    detector._keyword_cache = {
        "en": [
            CrisisKeywordRule(
                language="en",
                category="self_harm",
                pattern="hurt myself",
                regex=False,
            )
        ]
    }

    async def fake_classify(*args, **kwargs) -> CrisisClassification:
        return CrisisClassification("crisis", 0.55, "self_harm", False)

    async def fake_get_contacts(language: str | None) -> list[CrisisContactInfo]:
        return [_contact()]

    flagged_ids: list[object] = []

    async def fake_flag(message_id) -> None:
        flagged_ids.append(message_id)

    monkeypatch.setattr(detector, "_classify", fake_classify)
    monkeypatch.setattr(detector, "get_contacts", fake_get_contacts)
    monkeypatch.setattr(detector, "_flag_message_as_crisis", fake_flag)

    message_id = uuid4()
    result = await detector.before_llm_cb(
        _chat_ctx("I want to hurt myself"),
        session_language="en",
        user_message_id=message_id,
    )

    assert result is not None
    assert result.category == "self_harm"
    assert flagged_ids == [message_id]


@pytest.mark.asyncio
async def test_contacts_cache_and_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = _detector()
    calls: list[str] = []

    async def fake_fetch(language: str) -> list[CrisisContactInfo]:
        calls.append(language)
        if language == "fr":
            return []
        return [_contact()]

    monkeypatch.setattr(detector, "_fetch_contacts_for_language", fake_fetch)

    first = await detector.get_contacts("fr")
    second = await detector.get_contacts("fr")

    assert first == [_contact()]
    assert second == [_contact()]
    assert calls == ["fr", "en"]


@pytest.mark.asyncio
async def test_disabled_detector_skips_processing() -> None:
    detector = CrisisDetector(
        sessionmaker=lambda: None,  # type: ignore[arg-type]
        base_url="http://litellm:4000",
        api_key="test-key",
        model="gemini-flash-lite",
        enabled=False,
        http_client=_FakeClient(),  # type: ignore[arg-type]
    )

    result = await detector.before_llm_cb(_chat_ctx("I want to kill myself"), session_language="en")

    assert result is None


@pytest.mark.asyncio
async def test_proactive_message_is_skipped_even_with_keyword_match() -> None:
    detector = _detector()
    detector._keyword_cache = {
        "en": [
            CrisisKeywordRule(
                language="en",
                category="suicide",
                pattern="kill myself",
                regex=False,
            )
        ]
    }
    chat_ctx = llm.ChatContext(
        items=[
            llm.ChatMessage(role="system", content=["System"]),
            llm.ChatMessage(
                role="user",
                content=["I want to kill myself"],
                extra={"proactive": True},
            ),
        ]
    )

    result = await detector.before_llm_cb(chat_ctx, session_language="en")

    assert result is None


@pytest.mark.asyncio
async def test_llm_node_uses_crisis_override_and_skips_rag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeRagEngine:
        async def search(self, *_args, **_kwargs):
            raise AssertionError("RAG must be skipped during crisis override")

    class FakeDetector:
        async def before_llm_cb(self, *_args, **_kwargs):
            return _intervention()

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx

        async def _gen():
            yield "Please call 988 right now."

        return _gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    agent = agent_module.TwypeAgent(
        instructions="System",
        mode_voice_guidance="Voice guidance",
        mode_text_guidance="Text guidance",
        rag_engine=FakeRagEngine(),
        crisis_detector=FakeDetector(),  # type: ignore[arg-type]
    )

    stream = await agent.llm_node(_chat_ctx("I want to kill myself"), [], None)
    tokens = [chunk async for chunk in stream]

    assert tokens == ["Please call 988 right now."]
    assert agent.current_crisis_intervention is not None
    resolved_ctx = captured["chat_ctx"]
    assert isinstance(resolved_ctx, llm.ChatContext)
    assert resolved_ctx.items[0].text_content == "Crisis prompt"


@pytest.mark.asyncio
async def test_pipeline_resumes_normal_flow_after_crisis_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_contexts: list[llm.ChatContext] = []

    class FakeRagEngine:
        def __init__(self) -> None:
            self.calls = 0

        async def search(self, *_args, **_kwargs):
            self.calls += 1
            return []

    class FakeDetector:
        def __init__(self) -> None:
            self.calls = 0

        async def before_llm_cb(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return _intervention()
            return None

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured_contexts.append(chat_ctx)

        async def _gen():
            yield "ok"

        return _gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    rag_engine = FakeRagEngine()
    agent = agent_module.TwypeAgent(
        instructions="System",
        mode_voice_guidance="Voice guidance",
        mode_text_guidance="Text guidance",
        rag_engine=rag_engine,
        crisis_detector=FakeDetector(),  # type: ignore[arg-type]
    )

    first = await agent.llm_node(_chat_ctx("I want to kill myself"), [], None)
    _ = [chunk async for chunk in first]
    agent.clear_current_response_id()

    second = await agent.llm_node(_chat_ctx("Tell me about grounding"), [], None)
    _ = [chunk async for chunk in second]

    assert rag_engine.calls == 1
    assert len(captured_contexts[0].items) == 2
    assert captured_contexts[1].items[0].role == "system"


@pytest.mark.asyncio
async def test_crisis_turn_publishes_alert_and_delivers_plain_text_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published_alerts: list[CrisisIntervention] = []
    published_messages: list[str] = []

    class FakeDetector:
        async def before_llm_cb(self, *_args, **_kwargs):
            return _intervention()

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        async def _gen():
            yield "Please call 988 right now."

        return _gen()

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    agent = agent_module.TwypeAgent(
        instructions="System",
        mode_voice_guidance="Voice guidance",
        mode_text_guidance="Text guidance",
        crisis_detector=FakeDetector(),  # type: ignore[arg-type]
    )
    agent.mode_context.switch_to("text")
    agent.set_crisis_alert_publisher(lambda intervention: _capture(published_alerts, intervention))
    agent.set_chat_response_publisher(lambda text: _capture(published_messages, text))

    llm_stream = await agent.llm_node(_chat_ctx("I want to kill myself"), [], None)
    result = await agent.tts_node(llm_stream, None)

    assert result is None
    assert len(published_alerts) == 1
    assert published_alerts[0].category == "suicide"
    assert published_messages == ["Please call 988 right now."]

    completed = agent.consume_completed_response()
    assert completed is not None
    assert completed.crisis_intervention is not None
    assert completed.dual_layer_result.text_items == []
    assert completed.dual_layer_result.voice_text == "Please call 988 right now."


async def _capture(target: list, value) -> None:
    target.append(value)
