from __future__ import annotations


def normalize_language_code(language: str | None, *, multi: str | None = None) -> str | None:
    if language is None:
        return None

    cleaned = language.strip().lower()
    if not cleaned:
        return None

    if cleaned == "multi":
        return multi

    return cleaned.replace("_", "-").split("-", maxsplit=1)[0]
