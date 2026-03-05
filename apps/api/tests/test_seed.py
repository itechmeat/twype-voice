from __future__ import annotations

import importlib
import sys
from contextlib import asynccontextmanager
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_seed_agent_config_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    passlib_module = ModuleType("passlib")
    passlib_context_module = ModuleType("passlib.context")

    class FakeCryptContext:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def hash(self, plaintext: str) -> str:
            return f"hashed:{plaintext}"

    passlib_context_module.CryptContext = FakeCryptContext

    monkeypatch.setitem(sys.modules, "passlib", passlib_module)
    monkeypatch.setitem(sys.modules, "passlib.context", passlib_context_module)
    monkeypatch.delitem(sys.modules, "scripts.seed", raising=False)
    seed_module = importlib.import_module("scripts.seed")
    monkeypatch.setitem(sys.modules, "scripts.seed", seed_module)

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
