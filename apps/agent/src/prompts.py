from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from localization import build_locale_fallback_chain, normalize_locale
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("twype-agent")

DEFAULT_PROMPT_LOCALE = "en"

PROMPT_LAYER_ORDER = [
    "system_prompt",
    "voice_prompt",
    "language_prompt",
    "dual_layer_prompt",
    "emotion_prompt",
    "crisis_prompt",
    "rag_prompt",
    "proactive_prompt",
]
MODE_GUIDANCE_KEYS = [
    "mode_voice_guidance",
    "mode_text_guidance",
]

_PROMPT_BUNDLE_QUERY = sa.text(
    """
    SELECT key, locale, value, version
    FROM agent_configs
    WHERE is_active = true
      AND key IN :keys
      AND locale IN :locales
    """
).bindparams(
    sa.bindparam("keys", expanding=True),
    sa.bindparam("locales", expanding=True),
)

_SESSION_PREFERENCES_QUERY = sa.text(
    """
    SELECT users.preferences
    FROM sessions
    JOIN users ON users.id = sessions.user_id
    WHERE sessions.id = :session_id
    """
)

_UPDATE_SNAPSHOT_QUERY = sa.text(
    """
    UPDATE sessions
    SET agent_config_snapshot = :snapshot
    WHERE id = :session_id
    """
).bindparams(sa.bindparam("snapshot", type_=JSONB))


@dataclass(frozen=True, slots=True)
class PromptBundle:
    requested_locale: str
    locale_chain: tuple[str, ...]
    layers: dict[str, str]
    versions: dict[str, int]
    resolved_locales: dict[str, str]


class _PartialFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


async def resolve_prompt_locale(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    session_id: UUID | None,
    *,
    preferred_locale: str | None,
    default_locale: str = DEFAULT_PROMPT_LOCALE,
) -> str:
    if session_id is not None:
        async with db_sessionmaker() as session:
            result = await session.execute(
                _SESSION_PREFERENCES_QUERY,
                {"session_id": session_id},
            )
            preferences = result.scalar_one_or_none()

        if isinstance(preferences, dict):
            for key in ("locale", "language"):
                value = preferences.get(key)
                if isinstance(value, str) and value.strip():
                    return normalize_locale(value, default_locale=default_locale)

    return normalize_locale(preferred_locale, default_locale=default_locale)


async def load_prompt_bundle(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    locale: str,
    *,
    default_locale: str = DEFAULT_PROMPT_LOCALE,
) -> PromptBundle:
    locale_chain = build_locale_fallback_chain(locale, default_locale=default_locale)
    priority_by_locale = {value: index for index, value in enumerate(locale_chain)}

    async with db_sessionmaker() as session:
        result = await session.execute(
            _PROMPT_BUNDLE_QUERY,
            {
                "keys": [*PROMPT_LAYER_ORDER, *MODE_GUIDANCE_KEYS],
                "locales": list(locale_chain),
            },
        )
        rows = result.mappings().all()

    selected_rows: dict[str, dict[str, object]] = {}
    for row in rows:
        key = str(row["key"])
        row_locale = normalize_locale(str(row["locale"]), default_locale=default_locale)
        current_row = selected_rows.get(key)
        if current_row is None:
            selected_rows[key] = dict(row)
            continue

        current_locale = normalize_locale(str(current_row["locale"]), default_locale=default_locale)
        row_priority = priority_by_locale.get(row_locale)
        current_priority = priority_by_locale.get(current_locale)
        if row_priority is not None and (
            current_priority is None or row_priority < current_priority
        ):
            selected_rows[key] = dict(row)

    layers: dict[str, str] = {}
    versions: dict[str, int] = {}
    resolved_locales: dict[str, str] = {}

    for key in [*PROMPT_LAYER_ORDER, *MODE_GUIDANCE_KEYS]:
        row = selected_rows.get(key)
        if row is None:
            continue
        layers[key] = str(row["value"])
        versions[key] = int(row["version"])
        resolved_locales[key] = normalize_locale(str(row["locale"]), default_locale=default_locale)

    if not layers:
        raise RuntimeError(f"no prompt layers found for locale chain {locale_chain}")

    return PromptBundle(
        requested_locale=normalize_locale(locale, default_locale=default_locale),
        locale_chain=locale_chain,
        layers=layers,
        versions=versions,
        resolved_locales=resolved_locales,
    )


async def load_prompt_layers(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    locale: str,
    *,
    default_locale: str = DEFAULT_PROMPT_LOCALE,
) -> dict[str, str]:
    bundle = await load_prompt_bundle(
        db_sessionmaker,
        locale,
        default_locale=default_locale,
    )
    return bundle.layers


def build_instructions(layers: dict[str, str]) -> str:
    ordered_layers = [
        value.strip() for key in PROMPT_LAYER_ORDER if (value := layers.get(key)) and value.strip()
    ]
    return "\n\n".join(ordered_layers)


def require_prompt_layer(layers: dict[str, str], key: str) -> str:
    value = layers.get(key)
    if value is None or not value.strip():
        raise RuntimeError(f"prompt layer '{key}' is required")
    return value.strip()


def _neutral_emotional_defaults() -> dict[str, str]:
    from emotional_analyzer import get_tone_guidance

    return {
        "quadrant": "neutral",
        "valence": "0.0",
        "arousal": "0.0",
        "trend_valence": "stable",
        "trend_arousal": "stable",
        "tone_guidance": get_tone_guidance("neutral"),
    }


NEUTRAL_EMOTIONAL_DEFAULTS: dict[str, str] = _neutral_emotional_defaults()


def render_emotional_context(instructions: str, emotional_vars: dict[str, str] | None) -> str:
    resolved = {
        **NEUTRAL_EMOTIONAL_DEFAULTS,
        **(emotional_vars or {}),
    }
    try:
        return instructions.format_map(_PartialFormatDict(resolved))
    except (ValueError, IndexError):
        logger.warning("failed to render emotional context into instructions")
        return instructions


async def save_config_snapshot(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    session_id: UUID,
    prompt_bundle: PromptBundle,
) -> None:
    async with db_sessionmaker() as session:
        snapshot = {
            **prompt_bundle.layers,
            "_version": prompt_bundle.versions,
            "_meta": {
                "snapshot_at": datetime.now(UTC).isoformat(),
                "requested_locale": prompt_bundle.requested_locale,
                "locale_chain": list(prompt_bundle.locale_chain),
                "resolved_locales": prompt_bundle.resolved_locales,
            },
        }

        await session.execute(
            _UPDATE_SNAPSHOT_QUERY,
            {
                "session_id": session_id,
                "snapshot": snapshot,
            },
        )
        await session.commit()
