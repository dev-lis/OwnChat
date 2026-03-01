from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SendTextMessageRequest(BaseModel):
    type: Literal["text"]
    content: str = Field(min_length=1)
    client_message_id: str


class SendImageMessageRequest(BaseModel):
    type: Literal["image"]
    attachment_id: str
    client_message_id: str


class ReadMessageRequest(BaseModel):
    message_id: str
    read_at: str
