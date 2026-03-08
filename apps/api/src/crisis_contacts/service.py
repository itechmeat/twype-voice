from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.localization import normalize_locale
from src.models.crisis_contact import CrisisContact


def normalize_contact_language(language: str | None) -> str:
    normalized = normalize_locale(language, default_locale="en")
    return normalized.split("-", maxsplit=1)[0]


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
