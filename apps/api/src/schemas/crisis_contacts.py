from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class CrisisContactItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    language: str
    locale: str | None
    contact_type: str
    name: str
    phone: str | None
    url: str | None
    description: str
    priority: int
