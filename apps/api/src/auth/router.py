from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_session
from src.auth.exceptions import (
    AuthError,
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
from src.localization import resolve_request_locale, translate
from src.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_AUTH_ERROR_MAP: dict[type[AuthError], tuple[int, str]] = {
    EmailAlreadyRegisteredError: (status.HTTP_409_CONFLICT, "auth.email_already_registered"),
    UserNotFoundError: (status.HTTP_404_NOT_FOUND, "auth.user_not_found"),
    InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, "auth.invalid_credentials"),
    EmailNotVerifiedError: (status.HTTP_403_FORBIDDEN, "auth.email_not_verified"),
    InvalidVerificationCodeError: (status.HTTP_400_BAD_REQUEST, "auth.invalid_verification_code"),
    VerificationCodeExpiredError: (status.HTTP_400_BAD_REQUEST, "auth.verification_code_expired"),
    UserAlreadyVerifiedError: (status.HTTP_400_BAD_REQUEST, "auth.user_already_verified"),
    InvalidTokenError: (status.HTTP_401_UNAUTHORIZED, "auth.invalid_token"),
    InvalidTokenTypeError: (status.HTTP_401_UNAUTHORIZED, "auth.invalid_token_type"),
}


def _raise_for_auth_error(exc: AuthError, *, locale: str) -> NoReturn:
    entry = _AUTH_ERROR_MAP.get(type(exc))
    if entry is not None:
        code, detail_key = entry
        raise HTTPException(
            status_code=code,
            detail=translate(detail_key, locale=locale),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=translate("auth.unexpected_error", locale=locale),
    ) from exc


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    locale = resolve_request_locale(request.headers.get("Accept-Language"))
    try:
        await register_user(body.email, body.password, session, locale=locale)
    except AuthError as exc:
        _raise_for_auth_error(exc, locale=locale)
    return RegisterResponse(
        message=translate("auth.registration_success", locale=locale),
        email=body.email,
    )


@router.post("/verify", response_model=TokenResponse)
async def verify(
    body: VerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    locale = resolve_request_locale(request.headers.get("Accept-Language"))
    try:
        tokens = await verify_user(body.email, body.code, session)
    except AuthError as exc:
        _raise_for_auth_error(exc, locale=locale)
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    locale = resolve_request_locale(request.headers.get("Accept-Language"))
    try:
        return await login_user(body.email, body.password, session)
    except AuthError as exc:
        _raise_for_auth_error(exc, locale=locale)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    locale = resolve_request_locale(request.headers.get("Accept-Language"))
    try:
        return await refresh_tokens(body.refresh_token, session)
    except AuthError as exc:
        _raise_for_auth_error(exc, locale=locale)
