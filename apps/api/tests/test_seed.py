from __future__ import annotations

import importlib
import re
import sys
from contextlib import asynccontextmanager
from types import ModuleType

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.models import KnowledgeChunk, KnowledgeSource


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

    await seed_module.seed_knowledge_data()
    await seed_module.seed_knowledge_data()

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
