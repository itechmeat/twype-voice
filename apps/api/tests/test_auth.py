from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.jwt import create_access_token, create_refresh_token
from src.localization import translate
from src.models.user import User

from tests.helpers import create_verified_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(client: AsyncClient, email: str, password: str = "strongpass123"):
    return await client.post("/auth/register", json={"email": email, "password": password})


async def _get_verification_code(session: AsyncSession, email: str) -> str:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    return user.verification_code


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_successful_registration(self, client: AsyncClient, unique_email: str):
        resp = await _register(client, unique_email)
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "Verification code sent"
        assert data["email"] == unique_email

    async def test_duplicate_email(self, client: AsyncClient, unique_email: str):
        await _register(client, unique_email)
        resp = await _register(client, unique_email)
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    async def test_short_password(self, client: AsyncClient, unique_email: str):
        resp = await _register(client, unique_email, password="short")
        assert resp.status_code == 422

    async def test_registration_removes_user_when_email_delivery_fails(
        self,
        client: AsyncClient,
        session: AsyncSession,
        unique_email: str,
        monkeypatch,
    ):
        async def fail_send(*_args, **_kwargs) -> None:
            raise RuntimeError("email delivery failed")

        monkeypatch.setattr("src.auth.service.send_verification_code", fail_send)

        with pytest.raises(RuntimeError, match="email delivery failed"):
            await _register(client, unique_email)

        result = await session.execute(select(User).where(User.email == unique_email))
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


class TestVerify:
    async def _register_and_get_code(
        self, client: AsyncClient, session: AsyncSession, email: str
    ) -> str:
        await _register(client, email)
        await session.commit()
        return await _get_verification_code(session, email)

    async def test_successful_verification(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        code = await self._register_and_get_code(client, session, unique_email)
        resp = await client.post("/auth/verify", json={"email": unique_email, "code": code})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_expired_code(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        code = await self._register_and_get_code(client, session, unique_email)
        result = await session.execute(select(User).where(User.email == unique_email))
        user = result.scalar_one()
        user.verification_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

        resp = await client.post("/auth/verify", json={"email": unique_email, "code": code})
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    async def test_invalid_code(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        await self._register_and_get_code(client, session, unique_email)
        resp = await client.post("/auth/verify", json={"email": unique_email, "code": "000000"})
        assert resp.status_code == 400
        assert "invalid" in resp.json()["detail"].lower()

    async def test_already_verified(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        code = await self._register_and_get_code(client, session, unique_email)
        await client.post("/auth/verify", json={"email": unique_email, "code": code})
        resp = await client.post("/auth/verify", json={"email": unique_email, "code": code})
        assert resp.status_code == 400
        assert "already verified" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_successful_login(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        await create_verified_user(session, unique_email)
        await session.commit()
        resp = await client.post(
            "/auth/login", json={"email": unique_email, "password": "strongpass123"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_wrong_password(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        await create_verified_user(session, unique_email)
        await session.commit()
        resp = await client.post(
            "/auth/login", json={"email": unique_email, "password": "wrongpass123"}
        )
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()

    async def test_unverified_user(self, client: AsyncClient, unique_email: str):
        await _register(client, unique_email)
        resp = await client.post(
            "/auth/login", json={"email": unique_email, "password": "strongpass123"}
        )
        assert resp.status_code == 403
        assert "not verified" in resp.json()["detail"].lower()

    async def test_nonexistent_user(self, client: AsyncClient):
        resp = await client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
        )
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    async def test_successful_refresh(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()
        refresh_token = create_refresh_token(user.id)
        resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_expired_refresh_token(self, client: AsyncClient):
        fake_id = uuid.uuid4()
        with patch("src.auth.jwt.REFRESH_TOKEN_EXPIRE_DAYS", -1):
            token = create_refresh_token(fake_id)
        resp = await client.post("/auth/refresh", json={"refresh_token": token})
        assert resp.status_code == 401

    async def test_invalid_refresh_token(self, client: AsyncClient):
        resp = await client.post("/auth/refresh", json={"refresh_token": "not.a.valid.token"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Middleware (get_current_user) — tested via GET /me
# ---------------------------------------------------------------------------


class TestMiddleware:
    async def test_valid_token(self, client: AsyncClient, session: AsyncSession, unique_email: str):
        user = await create_verified_user(session, unique_email)
        await session.commit()
        token = create_access_token(user.id)
        resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == unique_email

    async def test_missing_header(self, client: AsyncClient):
        resp = await client.get("/me", headers={"Accept-Language": "en-US,en;q=0.9"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == translate(
            "auth.invalid_authentication_credentials",
            locale="en-US",
        )

    async def test_expired_access_token(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()
        with patch("src.auth.jwt.ACCESS_TOKEN_EXPIRE_MINUTES", -1):
            token = create_access_token(user.id)
        resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    async def test_refresh_token_as_access(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()
        token = create_refresh_token(user.id)
        resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == translate("auth.invalid_token_type")

    async def test_user_not_found(self, client: AsyncClient):
        token = create_access_token(uuid.uuid4())
        resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == translate("auth.user_not_found")

    async def test_unverified_user_with_token(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        pw_hash = bcrypt.hashpw(b"strongpass123", bcrypt.gensalt()).decode()
        user = User(email=unique_email, password_hash=pw_hash, is_verified=False)
        session.add(user)
        await session.flush()
        await session.commit()

        token = create_access_token(user.id)
        resp = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.json()["detail"] == translate("auth.email_not_verified")
