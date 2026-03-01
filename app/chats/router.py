from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_user_id
from app.chats.models import CreateChatRequest
from app.core.time import now_iso
from app.state.store import CHATS, MESSAGES_BY_CHAT

router = APIRouter(prefix="/api/v1/chats", tags=["Chats"])


@router.get("")
def list_chats(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user_id: str = Depends(require_user_id),
) -> dict[str, Any]:
    chats_for_user: list[dict[str, Any]] = []
    for chat in CHATS.values():
        if user_id not in chat["participant_ids"]:
            continue
        messages = MESSAGES_BY_CHAT.get(chat["chat_id"], [])
        last_message = messages[-1] if messages else None
        chats_for_user.append(
            {
                "chat_id": chat["chat_id"],
                "title": chat["title"],
                "last_message": (
                    {
                        "id": last_message["id"],
                        "type": last_message["type"],
                        "content_preview": (last_message.get("content") or "")[:120],
                        "created_at": last_message["created_at"],
                    }
                    if last_message
                    else None
                ),
                "unread_count": 0,
                "updated_at": chat["updated_at"],
            }
        )

    chats_for_user.sort(key=lambda item: item["updated_at"], reverse=True)
    start = int(cursor) if cursor and cursor.isdigit() else 0
    chunk = chats_for_user[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(chats_for_user) else None
    return {"items": chunk, "next_cursor": next_cursor}


@router.post("", status_code=201)
def create_chat(body: CreateChatRequest, user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    participant_ids = sorted(set(body.participant_ids + [user_id]))
    chat_id = str(uuid4())
    created_at = now_iso()
    CHATS[chat_id] = {
        "chat_id": chat_id,
        "participant_ids": participant_ids,
        "title": body.title or "New chat",
        "created_at": created_at,
        "updated_at": created_at,
    }
    MESSAGES_BY_CHAT[chat_id] = []
    return {"chat_id": chat_id, "created_at": created_at}
