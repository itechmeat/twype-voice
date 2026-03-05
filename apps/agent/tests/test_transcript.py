from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from src.models.base import Base
from src.models.message import Message
from src.models.session import Session
from src.models.user import User
from transcript import (
    configure_transcript_store,
    resolve_session_id,
    save_agent_response,
    save_transcript,
)


def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://twype:twype_secret@localhost:5433/twype_test",
        ),
    )


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_test_database_url(), echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def sessionmaker(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def seeded_session(sessionmaker: async_sessionmaker[AsyncSession]) -> Session:
    async with sessionmaker() as session:
        user = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
        session.add(user)
        await session.flush()

        room_name = f"session-{uuid.uuid4()}"
        db_session = Session(user_id=user.id, room_name=room_name, status="active")
        session.add(db_session)
        await session.commit()
        await session.refresh(db_session)
        return db_session


@pytest.mark.asyncio
async def test_resolve_session_id(sessionmaker, seeded_session: Session) -> None:
    configure_transcript_store(sessionmaker)

    resolved = await resolve_session_id(seeded_session.room_name)
    assert resolved == seeded_session.id


@pytest.mark.asyncio
async def test_save_transcript_inserts_row(sessionmaker, seeded_session: Session) -> None:
    configure_transcript_store(sessionmaker)

    inserted_id = await save_transcript(seeded_session.id, " Hello ", 0.1)
    assert inserted_id is not None

    async with sessionmaker() as session:
        msg = await session.get(Message, inserted_id)
        assert msg is not None
        assert msg.session_id == seeded_session.id
        assert msg.role == "user"
        assert msg.mode == "voice"
        assert msg.content == "Hello"
        assert msg.voice_transcript == "Hello"
        assert msg.sentiment_raw == 0.1


@pytest.mark.asyncio
async def test_save_transcript_skips_empty(sessionmaker, seeded_session: Session) -> None:
    configure_transcript_store(sessionmaker)

    inserted_id = await save_transcript(seeded_session.id, "   ", None)
    assert inserted_id is None

    async with sessionmaker() as session:
        count = await session.scalar(select(Message).where(Message.session_id == seeded_session.id))
        assert count is None


@pytest.mark.asyncio
async def test_save_agent_response_inserts_row(sessionmaker, seeded_session: Session) -> None:
    configure_transcript_store(sessionmaker)

    inserted_id = await save_agent_response(seeded_session.id, " Hi ")
    assert inserted_id is not None

    async with sessionmaker() as session:
        msg = await session.get(Message, inserted_id)
        assert msg is not None
        assert msg.session_id == seeded_session.id
        assert msg.role == "assistant"
        assert msg.mode == "voice"
        assert msg.content == "Hi"
        assert msg.voice_transcript == "Hi"
        assert msg.sentiment_raw is None


@pytest.mark.asyncio
async def test_save_agent_response_skips_empty(sessionmaker, seeded_session: Session) -> None:
    configure_transcript_store(sessionmaker)

    inserted_id = await save_agent_response(seeded_session.id, "   ")
    assert inserted_id is None

    async with sessionmaker() as session:
        count = await session.scalar(select(Message).where(Message.session_id == seeded_session.id))
        assert count is None


@pytest.mark.asyncio
async def test_save_agent_response_returns_none_on_db_error(
    sessionmaker,
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_transcript_store(sessionmaker)

    import transcript as transcript_module

    class BrokenSessionmaker:
        def __call__(self) -> object:
            raise RuntimeError("boom")

    monkeypatch.setattr(transcript_module, "_sessionmaker", BrokenSessionmaker())

    inserted_id = await transcript_module.save_agent_response(seeded_session.id, "Hi")
    assert inserted_id is None
