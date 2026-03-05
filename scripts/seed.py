from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

import sqlalchemy as sa
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import insert
from src.database import session_scope
from src.models import AgentConfig, TTSConfig, User

logger = logging.getLogger(__name__)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PROMPT_LAYER_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "system_prompt": (
            "You are Twype, an expert AI assistant for professional topics. "
            "Help carefully, stay structured, and be explicit about the limits of your confidence. "
            "Do not invent facts, hide uncertainty, or provide dangerous instructions."
        ),
        "voice_prompt": (
            "In voice mode, respond naturally, briefly, and conversationally, "
            "usually in 2-5 sentences. "
            "Start with the main point, then offer one useful next step or a short clarification."
        ),
        "dual_layer_prompt": (
            "Structure each answer in two layers: "
            "a short voice-friendly version and a more precise "
            "text-channel formulation when it helps. "
            "Avoid unnecessary repetition and keep the meaning consistent."
        ),
        "emotion_prompt": (
            "Take the user's emotional signals into account: "
            "speak more calmly and gently during anxiety, "
            "add reassurance and clarity during confusion, "
            "and stay professional with a neutral tone."
        ),
        "crisis_prompt": (
            "Notice signs of crisis, self-harm, violence, or acute disorganization. "
            "In those cases, respond with empathy, avoid increasing risk, "
            "and gently recommend urgent help "
            "from qualified professionals and emergency services "
            "when the situation appears immediate."
        ),
        "rag_prompt": (
            "If knowledge base materials are available, rely on them first. "
            "Separate source-based facts from general reasoning "
            "and explicitly mention which materials "
            "you are relying on whenever possible."
        ),
        "language_prompt": (
            "Always adapt to the user's language and keep using it until the user switches. "
            "If the user mixes languages, choose the dominant language "
            "and avoid unnecessary code-switching."
        ),
        "proactive_prompt": (
            "If the user goes quiet, hesitates, or gives an incomplete answer, "
            "gently suggest a next step: "
            "a clarifying question, a short action plan, or a way to continue the conversation."
        ),
        "mode_voice_guidance": (
            "Current input mode is voice. Reply briefly, naturally, and conversationally. "
            "Prefer a spoken rhythm over heavy structure."
        ),
        "mode_text_guidance": (
            "Current input mode is text. Reply with more detail and clearer structure. "
            "Use concise sections or bullets when that improves readability."
        ),
    },
    "ru": {
        "mode_voice_guidance": (
            "Current input mode is voice. Reply briefly, naturally, and conversationally. "
            "Prioritize clarity for spoken delivery."
        ),
        "mode_text_guidance": (
            "Current input mode is text. Reply with more detail and stronger structure. "
            "Use short sections or bullets when they improve readability."
        ),
    }
}


def _require_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")


def _password_hash(plaintext: str) -> str:
    return pwd_context.hash(plaintext)


async def seed_user() -> None:
    plaintext = os.environ.get("TWYPE_SEED_TEST_USER_PLAINTEXT", "twype-test-user")
    password_hash = _password_hash(plaintext)

    stmt = insert(User).values(
        id=TEST_USER_ID,
        email="test@twype.local",
        password_hash=password_hash,
        is_verified=True,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.email],
        set_={
            "password_hash": stmt.excluded.password_hash,
            "is_verified": stmt.excluded.is_verified,
            "updated_at": sa.text("now()"),
        },
    )

    async with session_scope() as session:
        await session.execute(stmt)


async def seed_agent_config() -> None:
    async with session_scope() as session:
        for locale, prompt_layers in PROMPT_LAYER_TRANSLATIONS.items():
            for key, value in prompt_layers.items():
                stmt = insert(AgentConfig).values(
                    key=key,
                    locale=locale,
                    value=value,
                    version=1,
                    is_active=True,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=[AgentConfig.key, AgentConfig.locale],
                    set_={
                        "value": stmt.excluded.value,
                        "is_active": stmt.excluded.is_active,
                        "updated_at": sa.text("now()"),
                    },
                )
                await session.execute(stmt)


async def seed_tts_config() -> None:
    stmt = insert(TTSConfig).values(
        voice_id="inworld-default",
        model_id="inworld-tts-1.5-max",
        expressiveness=0.5,
        speed=1.0,
        language="ru",
        is_active=True,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[TTSConfig.voice_id],
        set_={
            "voice_id": stmt.excluded.voice_id,
            "model_id": stmt.excluded.model_id,
            "expressiveness": stmt.excluded.expressiveness,
            "speed": stmt.excluded.speed,
            "language": stmt.excluded.language,
            "is_active": stmt.excluded.is_active,
        },
    )

    async with session_scope() as session:
        await session.execute(stmt)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    _require_database_url()

    logger.info("Seeding database")
    await seed_user()
    await seed_agent_config()
    await seed_tts_config()
    logger.info("Seed complete")


if __name__ == "__main__":
    asyncio.run(main())
