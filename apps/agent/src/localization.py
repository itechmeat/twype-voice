"""Agent-local localization utilities.

Provides translate() and locale normalization without importing API internals.
"""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_LOCALE = "en"

_CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "agent.response_service_unavailable": (
            "Sorry, the response service is temporarily unavailable. Please try again."
        ),
    },
}


def normalize_locale(locale: str | None, *, default_locale: str = DEFAULT_LOCALE) -> str:
    raw_locale = (locale or "").strip().replace("_", "-")
    if not raw_locale or raw_locale.lower() == "multi":
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


def build_locale_fallback_chain(
    locale: str | None,
    *,
    default_locale: str = DEFAULT_LOCALE,
) -> tuple[str, ...]:
    normalized_locale = normalize_locale(locale, default_locale=default_locale)
    parts = normalized_locale.split("-")
    chain: list[str] = []

    while parts:
        candidate = "-".join(parts)
        if candidate not in chain:
            chain.append(candidate)
        parts.pop()

    if default_locale not in chain:
        chain.append(default_locale)

    return tuple(chain)


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


def translate(
    key: str,
    *,
    locale: str | None = None,
    default_locale: str = DEFAULT_LOCALE,
    params: Mapping[str, object] | None = None,
) -> str:
    resolved = resolve_locale(locale, default_locale=default_locale)
    catalog = _CATALOG.get(resolved) or _CATALOG.get(default_locale) or {}
    template = catalog.get(key) or _CATALOG.get(default_locale, {}).get(key)
    if template is None:
        raise KeyError(f"unknown localization key: {key}")

    if params is None:
        return template

    return template.format_map(dict(params))
