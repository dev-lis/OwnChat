from __future__ import annotations

from pydantic import BaseModel, Field


class CreateUploadRequest(BaseModel):
    content_type: str
    file_name: str
    size_bytes: int = Field(gt=0)
