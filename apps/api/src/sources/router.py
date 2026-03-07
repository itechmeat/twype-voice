from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, get_session
from src.models.user import User
from src.schemas.sources import ResolveSourcesRequest, ResolveSourcesResponse
from src.sources.service import resolve_chunks

router = APIRouter()


@router.post("/resolve", response_model=ResolveSourcesResponse)
async def resolve_source_chunks(
    payload: ResolveSourcesRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ResolveSourcesResponse:
    items = await resolve_chunks(payload.chunk_ids, db)
    return ResolveSourcesResponse(items=items)
