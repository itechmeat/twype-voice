from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["book", "video", "podcast", "article", "post"]


class ResolveSourcesRequest(BaseModel):
    chunk_ids: list[uuid.UUID] = Field(max_length=50)


class SourceItem(BaseModel):
    chunk_id: uuid.UUID
    source_type: SourceType
    title: str
    author: str | None = None
    url: str | None = None
    section: str | None = None
    page_range: str | None = None


class ResolveSourcesResponse(BaseModel):
    items: list[SourceItem]
