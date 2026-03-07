# ruff: noqa: E402

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import UUID

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import sqlalchemy as sa
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import insert
from src.database import session_scope
from src.knowledge_constants import EMBEDDING_DIMENSION
from src.knowledge_ingestion.loader import DatabaseLoader, PreparedSource
from src.knowledge_ingestion.types import EmbeddedChunk, ManifestSource
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
            "Format every answer in two explicit sections using these delimiters exactly: "
            "---VOICE--- and ---TEXT---. "
            "In ---VOICE---, write 2-5 natural conversational sentences suitable for speech. "
            "In ---TEXT---, write bullet points starting with - or * for the data channel. "
            "When you use knowledge base context, cite the referenced chunk numbers with [N] "
            "markers that match the injected context order, for example [1] or [2][4]. "
            "Do not invent source numbers. If a point is your own reasoning or synthesis, leave "
            "it without [N] markers. Keep the meaning aligned between both sections.\n\n"
            "Example:\n"
            "---VOICE---\n"
            "The quickest way to reduce acute stress is to slow the breath "
            "and reorient to the room. "
            "Start with one simple exercise, then decide on the next safe action.\n"
            "---TEXT---\n"
            "- A longer exhale can reduce physiological arousal [2]\n"
            "- Sensory grounding helps bring attention back to the present moment [1]\n"
            "- After the stress wave drops, choose one concrete next step"
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
    },
}

SAMPLE_KNOWLEDGE_SOURCE = ManifestSource(
    file="seed-sample.html",
    source_type="article",
    title="Grounding Techniques for Acute Stress",
    language="en",
    author="Twype Editorial",
    url="https://example.local/grounding-techniques",
    tags=["psychology", "stress", "grounding"],
)

SAMPLE_KNOWLEDGE_CHUNKS: list[EmbeddedChunk] = [
    EmbeddedChunk(
        content=(
            "Grounding techniques help people return attention to the present moment when acute "
            "stress, panic, or intrusive thoughts narrow their focus. A simple first step is to "
            "name five things you can see, four you can touch, three you can hear, two you can "
            "smell, and one you can taste."
        ),
        section="Sensory orientation",
        page_range=None,
        language="en",
        token_count=58,
        embedding=[((index % 17) + 1) / 1000 for index in range(EMBEDDING_DIMENSION)],
    ),
    EmbeddedChunk(
        content=(
            "Breathing exercises work best when the pace is slightly slower than the person's "
            "usual rhythm. One practical pattern is inhale for four counts, pause for one, and "
            "exhale for six. The longer exhale can reduce physiological arousal without requiring "
            "special equipment or a quiet room."
        ),
        section="Breathing reset",
        page_range=None,
        language="en",
        token_count=54,
        embedding=[((index % 23) + 2) / 1000 for index in range(EMBEDDING_DIMENSION)],
    ),
    EmbeddedChunk(
        content=(
            "After the immediate stress wave drops, it is useful to re-establish orientation: "
            "note where you are, what time it is, and what the next safe action will be. A short "
            "follow-up plan such as drinking water, texting a trusted person, or stepping outside "
            "can prevent the person from sliding back into confusion."
        ),
        section="Next safe action",
        page_range=None,
        language="en",
        token_count=57,
        embedding=[((index % 29) + 3) / 1000 for index in range(EMBEDDING_DIMENSION)],
    ),
]


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


async def seed_knowledge_data() -> None:
    loader = DatabaseLoader()
    prepared_source = PreparedSource(
        source=SAMPLE_KNOWLEDGE_SOURCE,
        chunks=SAMPLE_KNOWLEDGE_CHUNKS,
    )

    async with session_scope() as session:
        await loader.load(session, [prepared_source])


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    _require_database_url()

    logger.info("Seeding database")
    await seed_user()
    await seed_agent_config()
    await seed_tts_config()
    await seed_knowledge_data()
    logger.info("Seed complete")


if __name__ == "__main__":
    asyncio.run(main())
