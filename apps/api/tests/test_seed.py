from __future__ import annotations

import importlib
import re
import sys
from contextlib import asynccontextmanager
from types import ModuleType

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.models import AgentConfig, CrisisContact, KnowledgeChunk, KnowledgeSource


@pytest.fixture
def seed_module(monkeypatch: pytest.MonkeyPatch):
    passlib_module = ModuleType("passlib")
    passlib_context_module = ModuleType("passlib.context")

    class FakeCryptContext:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def hash(self, plaintext: str) -> str:
            return f"hashed:{plaintext}"

    passlib_context_module.CryptContext = FakeCryptContext

    monkeypatch.setitem(sys.modules, "passlib", passlib_module)
    monkeypatch.setitem(sys.modules, "passlib.context", passlib_context_module)
    monkeypatch.delitem(sys.modules, "scripts.seed", raising=False)
    seed_module = importlib.import_module("scripts.seed")
    monkeypatch.setitem(sys.modules, "scripts.seed", seed_module)
    return seed_module


@pytest.mark.asyncio
async def test_seed_agent_config_is_idempotent(
    seed_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    executed_statements: list[str] = []

    class FakeSession:
        async def execute(self, statement) -> None:
            executed_statements.append(str(statement))

    @asynccontextmanager
    async def fake_session_scope():
        yield FakeSession()

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)

    await seed_module.seed_agent_config()
    await seed_module.seed_agent_config()

    total_prompt_rows = sum(
        len(layers) for layers in seed_module.PROMPT_LAYER_TRANSLATIONS.values()
    )

    assert len(executed_statements) == total_prompt_rows * 2
    assert all("ON CONFLICT" in statement.upper() for statement in executed_statements)
    assert all(
        re.search(r"ON\s+CONFLICT\s*\(\s*key\s*,\s*locale\s*\)", statement, re.IGNORECASE)
        for statement in executed_statements
    )


@pytest.mark.asyncio
async def test_seed_crisis_contacts_is_idempotent(
    seed_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_statements: list[str] = []

    class FakeSession:
        async def execute(self, statement) -> None:
            executed_statements.append(str(statement))

    @asynccontextmanager
    async def fake_session_scope():
        yield FakeSession()

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)

    await seed_module.seed_crisis_contacts()
    await seed_module.seed_crisis_contacts()

    assert len(executed_statements) == len(seed_module.CRISIS_CONTACTS) * 2
    assert all("ON CONFLICT" in statement.upper() for statement in executed_statements)


@pytest.mark.asyncio
async def test_seed_crisis_keywords_is_idempotent(
    seed_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_statements: list[str] = []

    class FakeSession:
        async def execute(self, statement) -> None:
            executed_statements.append(str(statement))

    @asynccontextmanager
    async def fake_session_scope():
        yield FakeSession()

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)

    await seed_module.seed_crisis_keywords()
    await seed_module.seed_crisis_keywords()

    assert len(executed_statements) == len(seed_module.CRISIS_KEYWORD_PATTERNS) * 2
    assert all("ON CONFLICT" in statement.upper() for statement in executed_statements)
    assert all(
        re.search(r"ON\s+CONFLICT\s*\(\s*key\s*,\s*locale\s*\)", statement, re.IGNORECASE)
        for statement in executed_statements
    )


def test_seed_prompt_layers_are_complete_for_en_and_ru(seed_module) -> None:
    expected_keys = {
        "system_prompt",
        "voice_prompt",
        "dual_layer_prompt",
        "emotion_prompt",
        "crisis_prompt",
        "rag_prompt",
        "language_prompt",
        "proactive_prompt",
        "mode_voice_guidance",
        "mode_text_guidance",
    }

    assert set(seed_module.PROMPT_LAYER_TRANSLATIONS["en"]) == expected_keys
    assert set(seed_module.PROMPT_LAYER_TRANSLATIONS["ru"]) == expected_keys
    assert all(
        seed_module.PROMPT_LAYER_TRANSLATIONS[locale][key].strip()
        for locale in ("en", "ru")
        for key in expected_keys
    )
    assert all(
        seed_module.PROMPT_LAYER_TRANSLATIONS["ru"][key]
        != seed_module.PROMPT_LAYER_TRANSLATIONS["en"][key]
        for key in expected_keys
    )


def test_seed_crisis_contacts_cover_en_and_ru_locales(seed_module) -> None:
    contacts_by_locale: dict[tuple[str, str], list[dict[str, object]]] = {}

    for contact in seed_module.CRISIS_CONTACTS:
        locale_key = (str(contact["language"]), str(contact["locale"]))
        contacts_by_locale.setdefault(locale_key, []).append(contact)

    assert len(contacts_by_locale[("en", "US")]) >= 3
    assert len(contacts_by_locale[("ru", "RU")]) >= 3
    assert all(
        str(contact["phone"]).strip() and str(contact["description"]).strip()
        for contact in seed_module.CRISIS_CONTACTS
    )


@pytest.mark.asyncio
async def test_seed_tts_config_is_idempotent(
    seed_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_statements: list[object] = []

    class FakeSession:
        async def execute(self, statement) -> None:
            executed_statements.append(statement)

    @asynccontextmanager
    async def fake_session_scope():
        yield FakeSession()

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)

    await seed_module.seed_tts_config()
    await seed_module.seed_tts_config()

    assert len(executed_statements) == 2
    assert all("ON CONFLICT" in str(statement).upper() for statement in executed_statements)
    assert all(
        statement.compile().params["voice_id"] == "Olivia" for statement in executed_statements
    )
    assert all(
        statement.compile().params["model_id"] == "inworld-tts-1.5-max"
        for statement in executed_statements
    )


@pytest.mark.asyncio
async def test_seed_main_skips_test_user_by_default(
    seed_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example")
    monkeypatch.delenv("TWYPE_SEED_INCLUDE_TEST_USER", raising=False)

    async def fake_seed_user() -> None:
        calls.append("seed_user")

    async def fake_seed_agent_config() -> None:
        calls.append("seed_agent_config")

    async def fake_seed_crisis_contacts() -> None:
        calls.append("seed_crisis_contacts")

    async def fake_seed_crisis_keywords() -> None:
        calls.append("seed_crisis_keywords")

    async def fake_seed_tts_config() -> None:
        calls.append("seed_tts_config")

    async def fake_seed_knowledge_data(*, embedding_client=None) -> None:
        _ = embedding_client
        calls.append("seed_knowledge_data")

    monkeypatch.setattr(seed_module, "seed_user", fake_seed_user)
    monkeypatch.setattr(seed_module, "seed_agent_config", fake_seed_agent_config)
    monkeypatch.setattr(seed_module, "seed_crisis_contacts", fake_seed_crisis_contacts)
    monkeypatch.setattr(seed_module, "seed_crisis_keywords", fake_seed_crisis_keywords)
    monkeypatch.setattr(seed_module, "seed_tts_config", fake_seed_tts_config)
    monkeypatch.setattr(seed_module, "seed_knowledge_data", fake_seed_knowledge_data)

    await seed_module.main()

    assert calls == [
        "seed_agent_config",
        "seed_crisis_contacts",
        "seed_crisis_keywords",
        "seed_tts_config",
        "seed_knowledge_data",
    ]


@pytest.mark.asyncio
async def test_seed_knowledge_data_creates_source_and_chunks(
    seed_module,
    db_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    @asynccontextmanager
    async def fake_session_scope():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)

    class FakeEmbeddingClient:
        async def embed_inputs(self, inputs):
            return [[0.001] * 1536 for _ in inputs]

    await seed_module.seed_knowledge_data(embedding_client=FakeEmbeddingClient())
    await seed_module.seed_knowledge_data(embedding_client=FakeEmbeddingClient())

    async with factory() as session:
        source = await session.scalar(
            sa.select(KnowledgeSource).where(
                KnowledgeSource.title == seed_module.SAMPLE_KNOWLEDGE_SOURCE.title
            )
        )
        chunk_count = await session.scalar(sa.select(sa.func.count()).select_from(KnowledgeChunk))

    assert source is not None
    assert source.source_type == "article"
    assert source.language == "en"
    assert chunk_count == 3


@pytest.mark.asyncio
async def test_seed_crisis_data_creates_contacts_and_keyword_configs(
    seed_module,
    db_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    @asynccontextmanager
    async def fake_session_scope():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)

    await seed_module.seed_crisis_contacts()
    await seed_module.seed_crisis_keywords()
    await seed_module.seed_crisis_contacts()
    await seed_module.seed_crisis_keywords()

    async with factory() as session:
        contact_count = await session.scalar(sa.select(sa.func.count()).select_from(CrisisContact))
        crisis_configs = await session.scalars(
            sa.select(AgentConfig).where(AgentConfig.key.like("crisis_keywords_%"))
        )
        configs = list(crisis_configs)

    assert contact_count == len(seed_module.CRISIS_CONTACTS)
    assert {config.key for config in configs} == {"crisis_keywords_en", "crisis_keywords_ru"}
