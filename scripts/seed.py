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

PROMPT_LAYERS: dict[str, str] = {
    "system_prompt": "Ты — Twype. Это placeholder системного промпта.",
    "voice_prompt": "Placeholder: голосовой режим. Отвечай кратко и по делу.",
    "dual_layer_prompt": "Placeholder: dual-layer. Совмещай voice и text стратегию.",
    "emotion_prompt": "Placeholder: эмоции. Учитывай валентность и возбуждение.",
    "crisis_prompt": "Placeholder: кризис. При рисках советуй обратиться к специалисту.",
    "rag_prompt": "Placeholder: RAG. При наличии источников — используй их аккуратно.",
    "language_prompt": "Placeholder: язык. Русский по умолчанию, без жёстких ограничений.",
    "proactive_prompt": "Placeholder: проактивность. Иногда предлагай следующий шаг.",
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
        for key, value in PROMPT_LAYERS.items():
            stmt = insert(AgentConfig).values(
                key=key,
                value=value,
                version=1,
                is_active=True,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[AgentConfig.key],
                set_={
                    "value": stmt.excluded.value,
                    "version": stmt.excluded.version,
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
