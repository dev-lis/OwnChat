from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import require_user_id
from app.core.time import now_iso
from app.messages.models import ReadMessageRequest, SendImageMessageRequest, SendTextMessageRequest
from app.state.store import CHATS, MESSAGES_BY_CHAT

router = APIRouter(prefix="/api/v1/chats", tags=["Messages"])


@router.get("/{chat_id}/messages")
def get_messages(
    chat_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    direction: Literal["older", "newer"] = Query(default="older"),
    user_id: str = Depends(require_user_id),
) -> dict[str, Any]:
    chat = CHATS.get(chat_id)
    if not chat or user_id not in chat["participant_ids"]:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Chat not found"})

    messages = MESSAGES_BY_CHAT.get(chat_id, [])
    if not messages:
        return {"items": [], "next_cursor": None, "prev_cursor": None}

    idx = int(cursor) if cursor and cursor.isdigit() else (len(messages) if direction == "older" else 0)
    if direction == "older":
        start = max(0, idx - limit)
        items = messages[start:idx]
        next_cursor = str(start) if start > 0 else None
        prev_cursor = str(idx) if idx < len(messages) else None
    else:
        end = min(len(messages), idx + limit)
        items = messages[idx:end]
        next_cursor = str(end) if end < len(messages) else None
        prev_cursor = str(max(0, idx - limit)) if idx > 0 else None

    return {"items": items, "next_cursor": next_cursor, "prev_cursor": prev_cursor}


@router.post("/{chat_id}/messages", status_code=202)
def send_message(
    chat_id: str,
    body: SendTextMessageRequest | SendImageMessageRequest,
    user_id: str = Depends(require_user_id),
) -> dict[str, Any]:
    chat = CHATS.get(chat_id)
    if not chat or user_id not in chat["participant_ids"]:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Chat not found"})

    created_at = now_iso()
    message_id = str(uuid4())
    message: dict[str, Any] = {
        "id": message_id,
        "chat_id": chat_id,
        "author_id": user_id,
        "type": body.type,
        "content": getattr(body, "content", None),
        "attachment_id": getattr(body, "attachment_id", None),
        "created_at": created_at,
        "status": "sent",
    }
    MESSAGES_BY_CHAT[chat_id].append(message)
    chat["updated_at"] = created_at
    return {"message_id": message_id, "status": "sent", "created_at": created_at}


@router.post("/{chat_id}/messages/read")
def mark_as_read(
    chat_id: str,
    body: ReadMessageRequest,
    user_id: str = Depends(require_user_id),
) -> dict[str, Any]:
    chat = CHATS.get(chat_id)
    if not chat or user_id not in chat["participant_ids"]:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Chat not found"})

    for message in MESSAGES_BY_CHAT.get(chat_id, []):
        if message["id"] == body.message_id:
            message["status"] = "read"
            return {
                "chat_id": chat_id,
                "message_id": body.message_id,
                "user_id": user_id,
                "status": "read",
                "read_at": body.read_at,
            }
    raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Message not found"})
