from __future__ import annotations

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    participant_ids: list[str] = Field(default_factory=list)
    title: str | None = None
