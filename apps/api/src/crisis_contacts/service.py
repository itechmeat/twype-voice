from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.crisis_contact import CrisisContact


def normalize_contact_language(language: str | None) -> str:
    cleaned = (language or "en").strip().lower().replace("_", "-")
    if not cleaned:
        return "en"
    primary = cleaned.split("-", maxsplit=1)[0]
    return primary if primary else "en"


async def list_crisis_contacts(
    db: AsyncSession,
    *,
    language: str | None,
) -> list[CrisisContact]:
    requested_language = normalize_contact_language(language)

    async def _fetch(requested: str) -> list[CrisisContact]:
        result = await db.execute(
            select(CrisisContact)
            .where(
                CrisisContact.is_active.is_(True),
                CrisisContact.language == requested,
            )
            .order_by(CrisisContact.priority.asc(), CrisisContact.name.asc())
        )
        return list(result.scalars().all())

    contacts = await _fetch(requested_language)
    if contacts or requested_language == "en":
        return contacts

    return await _fetch("en")
