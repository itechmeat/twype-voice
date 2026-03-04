from __future__ import annotations


class AuthError(Exception):
    """Base auth exception."""


class EmailAlreadyRegisteredError(AuthError):
    pass


class UserNotFoundError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class EmailNotVerifiedError(AuthError):
    pass


class InvalidVerificationCodeError(AuthError):
    pass


class VerificationCodeExpiredError(AuthError):
    pass


class UserAlreadyVerifiedError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class InvalidTokenTypeError(AuthError):
    pass
