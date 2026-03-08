from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-32-bytes-min")
os.environ.setdefault("RESEND_API_KEY", "re_test_fake")
os.environ.setdefault("LIVEKIT_API_KEY", "lk_test_api_key")
os.environ.setdefault("LIVEKIT_API_SECRET", "lk_test_api_secret_with_32_bytes_min")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.auth.dependencies import get_session
from src.models.base import Base

from testsupport import (
    default_test_database_url,
    ensure_database_exists,
    ensure_pgvector_extension,
)

TEST_DATABASE_URL = default_test_database_url(os.environ, scope="api")


@pytest.fixture
async def db_engine():
    await ensure_database_exists(TEST_DATABASE_URL)
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await ensure_pgvector_extension(conn)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
async def client(db_engine) -> AsyncIterator[AsyncClient]:
    from src.main import app

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override() -> AsyncIterator[AsyncSession]:
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(autouse=True)
def _mock_resend():
    with patch("src.auth.email.resend") as mock:
        mock.Emails.send.return_value = {"id": "fake-email-id"}
        yield mock
