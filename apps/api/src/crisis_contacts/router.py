from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_session
from src.crisis_contacts.service import list_crisis_contacts
from src.schemas.crisis_contacts import CrisisContactItem

router = APIRouter()


@router.get("", response_model=list[CrisisContactItem])
async def get_crisis_contacts(
    language: Annotated[str | None, Query(min_length=2, max_length=10)] = None,
    db: AsyncSession = Depends(get_session),
) -> list[CrisisContactItem]:
    contacts = await list_crisis_contacts(db, language=language)
    return [CrisisContactItem.model_validate(contact, from_attributes=True) for contact in contacts]
