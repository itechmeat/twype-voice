from __future__ import annotations

import uuid

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.jwt import create_access_token
from src.models.user import User


async def create_verified_user(
    session: AsyncSession, email: str, password: str = "strongpass123"
) -> User:
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(email=email, password_hash=pw_hash, is_verified=True)
    session.add(user)
    await session.flush()
    return user


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}
