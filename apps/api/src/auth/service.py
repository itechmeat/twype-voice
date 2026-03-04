from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.email import send_verification_code
from src.auth.exceptions import (
    EmailAlreadyRegisteredError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidTokenTypeError,
    InvalidVerificationCodeError,
    UserAlreadyVerifiedError,
    UserNotFoundError,
    VerificationCodeExpiredError,
)
from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.models.user import User
from src.schemas.auth import TokenResponse

VERIFICATION_CODE_TTL_MINUTES = 10


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _generate_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def _make_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def _get_user_by_email(email: str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError
    return user


async def _get_user_by_id(user_id: uuid.UUID, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError
    return user


async def register_user(email: str, password: str, session: AsyncSession) -> None:
    user = User(
        email=email,
        password_hash=_hash_password(password),
        verification_code=_generate_code(),
        verification_expires_at=datetime.now(UTC)
        + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise EmailAlreadyRegisteredError from exc

    await send_verification_code(user.email, user.verification_code)


async def verify_user(email: str, code: str, session: AsyncSession) -> TokenResponse:
    user = await _get_user_by_email(email, session)

    if user.is_verified:
        raise UserAlreadyVerifiedError

    if user.verification_expires_at is None or datetime.now(UTC) > user.verification_expires_at:
        raise VerificationCodeExpiredError

    if not user.verification_code or not secrets.compare_digest(user.verification_code, code):
        raise InvalidVerificationCodeError

    user.is_verified = True
    user.verification_code = None
    user.verification_expires_at = None
    await session.flush()

    return _make_token_response(user)


async def login_user(email: str, password: str, session: AsyncSession) -> TokenResponse:
    try:
        user = await _get_user_by_email(email, session)
    except UserNotFoundError as exc:
        raise InvalidCredentialsError from exc

    if not _verify_password(password, user.password_hash):
        raise InvalidCredentialsError

    if not user.is_verified:
        raise EmailNotVerifiedError

    return _make_token_response(user)


async def refresh_tokens(refresh_token: str, session: AsyncSession) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise InvalidTokenError from exc

    if payload.get("type") != "refresh":
        raise InvalidTokenTypeError

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise InvalidTokenError from exc

    user = await _get_user_by_id(user_id, session)
    return _make_token_response(user)
