from __future__ import annotations

from collections.abc import Mapping

DEFAULT_LOCALE = "en"

_CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "agent.response_service_unavailable": (
            "Sorry, the response service is temporarily unavailable. Please try again."
        ),
        "auth.email_already_registered": "Email already registered",
        "auth.user_not_found": "User not found",
        "auth.invalid_credentials": "Invalid credentials",
        "auth.email_not_verified": "Email not verified",
        "auth.invalid_verification_code": "Invalid verification code",
        "auth.verification_code_expired": "Verification code has expired",
        "auth.user_already_verified": "User already verified",
        "auth.invalid_token": "Invalid token",
        "auth.invalid_token_type": "Invalid token type",
        "auth.registration_success": "Verification code sent",
        "auth.email_verification_subject": "Twype verification code",
        "auth.email_verification_html": (
            "<p>Your verification code: <strong>{code}</strong></p>"
            "<p>The code is valid for {ttl_minutes} minutes.</p>"
        ),
    }
}


def normalize_locale(locale: str | None, *, default_locale: str = DEFAULT_LOCALE) -> str:
    raw_locale = (locale or "").strip().replace("_", "-")
    if not raw_locale:
        return default_locale

    parts = [part for part in raw_locale.split("-") if part]
    if not parts:
        return default_locale

    normalized_parts = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 2 and part.isalpha():
            normalized_parts.append(part.upper())
        elif len(part) == 4 and part.isalpha():
            normalized_parts.append(part.title())
        else:
            normalized_parts.append(part)

    return "-".join(normalized_parts)


def resolve_locale(
    locale: str | None,
    *,
    default_locale: str = DEFAULT_LOCALE,
) -> str:
    normalized = normalize_locale(locale, default_locale=default_locale)
    parts = normalized.split("-")

    while parts:
        candidate = "-".join(parts)
        if candidate in _CATALOG:
            return candidate
        parts.pop()

    return default_locale


def resolve_request_locale(
    accept_language: str | None,
    *,
    default_locale: str = DEFAULT_LOCALE,
) -> str:
    if not accept_language:
        return default_locale

    for raw_part in accept_language.split(","):
        language = raw_part.split(";", maxsplit=1)[0].strip()
        if language:
            return resolve_locale(language, default_locale=default_locale)

    return default_locale


def translate(
    key: str,
    *,
    locale: str | None = None,
    default_locale: str = DEFAULT_LOCALE,
    params: Mapping[str, object] | None = None,
) -> str:
    resolved_locale = resolve_locale(locale, default_locale=default_locale)
    resolved_catalog = _CATALOG.get(resolved_locale)
    catalog = resolved_catalog if resolved_catalog is not None else _CATALOG[default_locale]
    template = catalog.get(key)
    if template is None:
        template = _CATALOG[default_locale].get(key)
    if template is None:
        raise KeyError(f"unknown localization key: {key}")

    if params is None:
        return template

    return template.format_map(dict(params))
