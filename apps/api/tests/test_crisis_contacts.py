from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.crisis_contact import CrisisContact


async def _create_contact(
    session: AsyncSession,
    *,
    language: str,
    priority: int,
    name: str,
    contact_type: str = "crisis_helpline",
    is_active: bool = True,
) -> CrisisContact:
    contact = CrisisContact(
        id=uuid.uuid4(),
        language=language,
        locale=language.upper(),
        contact_type=contact_type,
        name=name,
        phone=f"{priority:03d}",
        url=None,
        description=f"{name} description",
        priority=priority,
        is_active=is_active,
    )
    session.add(contact)
    await session.flush()
    return contact


class TestCrisisContactsEndpoint:
    async def test_returns_contacts_by_language(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        first = await _create_contact(session, language="ru", priority=1, name="A")
        second = await _create_contact(session, language="ru", priority=2, name="B")
        await _create_contact(session, language="en", priority=1, name="English")
        await session.commit()

        response = await client.get("/crisis-contacts?language=ru")

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": str(first.id),
                "language": "ru",
                "locale": "RU",
                "contact_type": "crisis_helpline",
                "name": "A",
                "phone": "001",
                "url": None,
                "description": "A description",
                "priority": 1,
            },
            {
                "id": str(second.id),
                "language": "ru",
                "locale": "RU",
                "contact_type": "crisis_helpline",
                "name": "B",
                "phone": "002",
                "url": None,
                "description": "B description",
                "priority": 2,
            },
        ]

    async def test_falls_back_to_english_when_language_missing(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        english = await _create_contact(session, language="en", priority=1, name="Lifeline")
        await _create_contact(session, language="fr", priority=1, name="French", is_active=False)
        await session.commit()

        response = await client.get("/crisis-contacts?language=fr")

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": str(english.id),
                "language": "en",
                "locale": "EN",
                "contact_type": "crisis_helpline",
                "name": "Lifeline",
                "phone": "001",
                "url": None,
                "description": "Lifeline description",
                "priority": 1,
            }
        ]

    async def test_is_public_without_authentication(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        await _create_contact(session, language="en", priority=1, name="Public Lifeline")
        await session.commit()

        response = await client.get("/crisis-contacts")

        assert response.status_code == 200
        assert response.json()[0]["name"] == "Public Lifeline"

    async def test_defaults_to_english_without_language_query(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ) -> None:
        await _create_contact(session, language="ru", priority=1, name="Russian")
        english = await _create_contact(session, language="en", priority=1, name="Default English")
        await session.commit()

        response = await client.get("/crisis-contacts")

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": str(english.id),
                "language": "en",
                "locale": "EN",
                "contact_type": "crisis_helpline",
                "name": "Default English",
                "phone": "001",
                "url": None,
                "description": "Default English description",
                "priority": 1,
            }
        ]
