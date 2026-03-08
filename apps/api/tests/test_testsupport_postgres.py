from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

import testsupport.postgres as postgres_support


def test_default_test_database_url_rejects_non_test_override() -> None:
    with pytest.raises(ValueError, match=r"\*_test"):
        postgres_support.default_test_database_url(
            {"TEST_DATABASE_URL": "postgresql+asyncpg://twype:secret@localhost:5432/twype"}
        )


def test_default_test_database_url_accepts_test_override() -> None:
    database_url = postgres_support.default_test_database_url(
        {"TEST_DATABASE_URL": "postgresql+asyncpg://twype:secret@localhost:5432/twype_test"}
    )

    assert database_url.endswith("/twype_test")


def test_default_test_database_url_applies_scope() -> None:
    database_url = postgres_support.default_test_database_url(
        {"TEST_DATABASE_URL": "postgresql+asyncpg://twype:secret@localhost:5432/twype_test"},
        scope="agent-rag",
    )

    assert database_url.endswith("/twype_agent_rag_test")


@pytest.mark.asyncio
async def test_ensure_database_exists_ignores_duplicate_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql+asyncpg://twype:secret@localhost:5432/twype_test"
    admin_url = make_url("postgresql+asyncpg://twype:secret@localhost:5432/postgres")

    class FakeDuplicateDatabaseError(Exception):
        pass

    class FakeConnection:
        def __init__(self) -> None:
            self.closed = False
            self.executed: list[str] = []

        async def fetchval(self, *_args, **_kwargs):
            return None

        async def execute(self, statement: str) -> None:
            self.executed.append(statement)
            raise FakeDuplicateDatabaseError()

        async def close(self) -> None:
            self.closed = True

    connection = FakeConnection()

    async def fake_connect(**_kwargs):
        return connection

    monkeypatch.setattr(postgres_support, "_admin_database_urls", lambda _url: [admin_url])
    monkeypatch.setattr(postgres_support.asyncpg, "connect", fake_connect)
    monkeypatch.setattr(
        postgres_support.asyncpg,
        "DuplicateDatabaseError",
        FakeDuplicateDatabaseError,
    )
    postgres_support._ensured_databases.clear()

    await postgres_support.ensure_database_exists(database_url)

    assert connection.executed == ['CREATE DATABASE "twype_test"']
    assert connection.closed is True
    assert database_url in postgres_support._ensured_databases
