from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.localization import translate
from src.models.message import Message
from src.models.session import Session

from tests.helpers import auth_headers, create_verified_user


class TestStartSession:
    async def test_success(self, client: AsyncClient, session: AsyncSession, unique_email: str):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        resp = await client.post("/sessions/start", headers=auth_headers(user.id))
        assert resp.status_code == 201
        data = resp.json()

        session_id = uuid.UUID(data["session_id"])
        assert data["room_name"].startswith("session-")
        assert isinstance(data["livekit_token"], str)
        assert data["livekit_token"].count(".") == 2

        result = await session.execute(select(Session).where(Session.id == session_id))
        created = result.scalar_one()
        assert created.user_id == user.id
        assert created.status == "active"
        assert created.room_name == data["room_name"]

    async def test_unauthorized(self, client: AsyncClient):
        resp = await client.post("/sessions/start")
        assert resp.status_code == 401


class TestSessionHistory:
    async def test_empty_list(self, client: AsyncClient, session: AsyncSession, unique_email: str):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        resp = await client.get("/sessions/history", headers=auth_headers(user.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_pagination_and_limit_clamp(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        now = datetime.now(UTC)
        sessions = []
        for idx in range(105):
            s = Session(
                user_id=user.id,
                room_name=f"session-{uuid.uuid4()}",
                status="active",
                started_at=now - timedelta(seconds=idx),
            )
            sessions.append(s)
        session.add_all(sessions)
        await session.commit()

        resp = await client.get("/sessions/history?limit=200", headers=auth_headers(user.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 105
        assert len(data["items"]) == 100

        resp2 = await client.get(
            "/sessions/history?offset=10&limit=5",
            headers=auth_headers(user.id),
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["total"] == 105
        assert len(data2["items"]) == 5

        items = data2["items"]
        started_at = [item["started_at"] for item in items]
        assert started_at == sorted(started_at, reverse=True)


class TestSessionMessages:
    async def test_own_messages_sorted_asc(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        s = Session(user_id=user.id, room_name=f"session-{uuid.uuid4()}", status="active")
        session.add(s)
        await session.flush()

        now = datetime.now(UTC)
        m2 = Message(
            session_id=s.id,
            role="assistant",
            mode="text",
            content="second",
            created_at=now + timedelta(seconds=1),
        )
        m1 = Message(
            session_id=s.id,
            role="user",
            mode="text",
            content="first",
            created_at=now,
        )
        session.add_all([m2, m1])
        await session.commit()

        resp = await client.get(f"/sessions/{s.id}/messages", headers=auth_headers(user.id))
        assert resp.status_code == 200
        data = resp.json()
        assert [m["content"] for m in data] == ["first", "second"]

    async def test_empty_list(self, client: AsyncClient, session: AsyncSession, unique_email: str):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        s = Session(user_id=user.id, room_name=f"session-{uuid.uuid4()}", status="active")
        session.add(s)
        await session.commit()

        resp = await client.get(f"/sessions/{s.id}/messages", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_includes_source_ids(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        s = Session(user_id=user.id, room_name=f"session-{uuid.uuid4()}", status="active")
        session.add(s)
        await session.flush()

        source_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        message = Message(
            session_id=s.id,
            role="assistant",
            mode="text",
            content="with sources",
            source_ids=source_ids,
        )
        session.add(message)
        await session.commit()

        resp = await client.get(f"/sessions/{s.id}/messages", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert resp.json()[0]["source_ids"] == source_ids

    async def test_other_users_session_is_404(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        owner = await create_verified_user(session, unique_email)
        attacker_email = f"attacker-{uuid.uuid4().hex[:8]}@example.com"
        attacker = await create_verified_user(session, attacker_email)
        await session.commit()

        s = Session(user_id=owner.id, room_name=f"session-{uuid.uuid4()}", status="active")
        session.add(s)
        await session.commit()

        resp = await client.get(f"/sessions/{s.id}/messages", headers=auth_headers(attacker.id))
        assert resp.status_code == 404
        assert resp.json()["detail"] == translate("sessions.session_not_found")
