from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_session
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
from src.auth.service import login_user, refresh_tokens, register_user, verify_user
from src.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_AUTH_ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    EmailAlreadyRegisteredError: (status.HTTP_409_CONFLICT, "Email already registered"),
    UserNotFoundError: (status.HTTP_404_NOT_FOUND, "User not found"),
    InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, "Invalid credentials"),
    EmailNotVerifiedError: (status.HTTP_403_FORBIDDEN, "Email not verified"),
    InvalidVerificationCodeError: (status.HTTP_400_BAD_REQUEST, "Invalid verification code"),
    VerificationCodeExpiredError: (status.HTTP_400_BAD_REQUEST, "Verification code has expired"),
    UserAlreadyVerifiedError: (status.HTTP_400_BAD_REQUEST, "User already verified"),
    InvalidTokenError: (status.HTTP_401_UNAUTHORIZED, "Invalid token"),
    InvalidTokenTypeError: (status.HTTP_401_UNAUTHORIZED, "Invalid token type"),
}


def _raise_for_auth_error(exc: Exception) -> None:
    for exc_type, (code, detail) in _AUTH_ERROR_MAP.items():
        if isinstance(exc, exc_type):
            raise HTTPException(status_code=code, detail=detail) from exc
    raise exc


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    try:
        await register_user(body.email, body.password, session)
    except Exception as exc:
        _raise_for_auth_error(exc)
    await session.commit()
    return RegisterResponse(message="Verification code sent", email=body.email)


@router.post("/verify", response_model=TokenResponse)
async def verify(body: VerifyRequest, session: AsyncSession = Depends(get_session)):
    try:
        tokens = await verify_user(body.email, body.code, session)
    except Exception as exc:
        _raise_for_auth_error(exc)
    await session.commit()
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await login_user(body.email, body.password, session)
    except Exception as exc:
        _raise_for_auth_error(exc)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await refresh_tokens(body.refresh_token, session)
    except Exception as exc:
        _raise_for_auth_error(exc)
