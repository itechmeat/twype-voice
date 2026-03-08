"""Shared chat context utility functions for agent and crisis modules."""

from __future__ import annotations

from languages import normalize_language_code
from livekit.agents import llm


def last_user_message(chat_ctx: llm.ChatContext | None) -> llm.ChatMessage | None:
    """Return the last user message from chat context, or None."""
    if chat_ctx is None:
        return None

    for item in reversed(chat_ctx.items):
        if isinstance(item, llm.ChatMessage) and item.role == "user":
            return item
    return None


def resolve_message_language(
    extra: dict[str, object],
    session_language: str | None,
) -> str:
    """Resolve language from message extra or session language, defaulting to 'en'."""
    for key in ("language", "locale"):
        value = extra.get(key)
        normalized = normalize_language_code(str(value)) if isinstance(value, str) else None
        if normalized:
            return normalized
    return normalize_language_code(session_language) or "en"
