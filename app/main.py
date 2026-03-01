from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent
OPENAPI_YAML_PATH = BASE_DIR / "docs" / "openapi.yaml"

app = FastAPI(
    title="OwnChat API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


class RequestOtpRequest(BaseModel):
    phone: str


class VerifyOtpRequest(BaseModel):
    otp_session_id: str
    code: str = Field(min_length=4, max_length=8)


class RegisterRequest(BaseModel):
    verification_token: str
    display_name: str = Field(min_length=1, max_length=64)
    avatar_url: str | None = None


class LoginRequest(BaseModel):
    verification_token: str
    device_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateChatRequest(BaseModel):
    participant_ids: list[str] = Field(default_factory=list)
    title: str | None = None


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


class CreateUploadRequest(BaseModel):
    content_type: str
    file_name: str
    size_bytes: int = Field(gt=0)


OTP_SESSIONS: dict[str, dict[str, Any]] = {}
VERIFICATION_TOKENS: dict[str, str] = {}
USERS_BY_PHONE: dict[str, dict[str, Any]] = {}
ACCESS_TOKENS: dict[str, str] = {}
REFRESH_TOKENS: dict[str, str] = {}
CHATS: dict[str, dict[str, Any]] = {}
MESSAGES_BY_CHAT: dict[str, list[dict[str, Any]]] = {}
ATTACHMENTS: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Missing bearer token"})

    token = authorization.removeprefix("Bearer ").strip()
    user_id = ACCESS_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid token"})

    return user_id


@app.get("/health", tags=["System"], summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/request-otp", tags=["Auth"])
def request_otp(body: RequestOtpRequest) -> dict[str, Any]:
    otp_session_id = str(uuid4())
    OTP_SESSIONS[otp_session_id] = {"phone": body.phone, "code": "123456", "verified": False, "created_at": now_iso()}
    return {"otp_session_id": otp_session_id, "expires_in": 300}


@app.post("/api/v1/auth/verify-otp", tags=["Auth"])
def verify_otp(body: VerifyOtpRequest) -> dict[str, Any]:
    session = OTP_SESSIONS.get(body.otp_session_id)
    if not session or body.code != session["code"]:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid OTP"})

    session["verified"] = True
    verification_token = str(uuid4())
    VERIFICATION_TOKENS[verification_token] = session["phone"]
    return {"verified": True, "verification_token": verification_token}


@app.post("/api/v1/auth/register", status_code=201, tags=["Auth"])
def register(body: RegisterRequest) -> dict[str, Any]:
    phone = VERIFICATION_TOKENS.get(body.verification_token)
    if not phone:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid verification token"})
    if phone in USERS_BY_PHONE:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "User already exists"})

    user_id = str(uuid4())
    USERS_BY_PHONE[phone] = {
        "user_id": user_id,
        "phone": phone,
        "display_name": body.display_name,
        "avatar_url": body.avatar_url,
        "created_at": now_iso(),
    }
    return {"user_id": user_id, "created_at": USERS_BY_PHONE[phone]["created_at"]}


@app.post("/api/v1/auth/login", tags=["Auth"])
def login(body: LoginRequest) -> dict[str, Any]:
    phone = VERIFICATION_TOKENS.get(body.verification_token)
    user = USERS_BY_PHONE.get(phone or "")
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "User is not registered"})

    access_token = str(uuid4())
    refresh_token = str(uuid4())
    ACCESS_TOKENS[access_token] = user["user_id"]
    REFRESH_TOKENS[refresh_token] = user["user_id"]
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
    }


@app.post("/api/v1/auth/refresh", tags=["Auth"])
def refresh(body: RefreshRequest) -> dict[str, Any]:
    user_id = REFRESH_TOKENS.get(body.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid refresh token"})

    access_token = str(uuid4())
    refresh_token = str(uuid4())
    ACCESS_TOKENS[access_token] = user_id
    REFRESH_TOKENS[refresh_token] = user_id
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
    }


@app.get("/api/v1/chats", tags=["Chats"])
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


@app.post("/api/v1/chats", status_code=201, tags=["Chats"])
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


@app.get("/api/v1/chats/{chat_id}/messages", tags=["Messages"])
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


@app.post("/api/v1/chats/{chat_id}/messages", status_code=202, tags=["Messages"])
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


@app.post("/api/v1/chats/{chat_id}/messages/read", tags=["Messages"])
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


@app.post("/api/v1/media/uploads", status_code=201, tags=["Media"])
def create_upload(body: CreateUploadRequest, user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    attachment_id = str(uuid4())
    ATTACHMENTS[attachment_id] = {
        "attachment_id": attachment_id,
        "owner_id": user_id,
        "content_type": body.content_type,
        "file_name": body.file_name,
        "size_bytes": body.size_bytes,
        "created_at": now_iso(),
    }
    return {
        "attachment_id": attachment_id,
        "upload_url": f"https://s3.example.com/upload/{attachment_id}",
        "expires_in": 300,
    }


@app.websocket("/ws/v1/connect")
async def ws_connect(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    auth_header = websocket.headers.get("authorization", "")
    if not token and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    if not token or token not in ACCESS_TOKENS:
        await websocket.close(code=1008)
        return

    user_id = ACCESS_TOKENS[token]
    await websocket.accept()
    await websocket.send_json({"event": "system.connected", "payload": {"user_id": user_id, "ts": now_iso()}})
    try:
        while True:
            event = await websocket.receive_json()
            name = event.get("event")
            payload = event.get("payload", {})
            if name in {"typing.start", "typing.stop"}:
                await websocket.send_json(
                    {
                        "event": "typing.update",
                        "payload": {
                            "chat_id": payload.get("chat_id"),
                            "user_id": user_id,
                            "is_typing": name == "typing.start",
                            "ts": now_iso(),
                        },
                    }
                )
            elif name == "message.read":
                await websocket.send_json(
                    {
                        "event": "message.read.updated",
                        "payload": {
                            "chat_id": payload.get("chat_id"),
                            "message_id": payload.get("message_id"),
                            "user_id": user_id,
                            "read_at": payload.get("read_at") or now_iso(),
                        },
                    }
                )
    except WebSocketDisconnect:
        return


def _load_openapi_from_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        parsed = yaml.safe_load(file)

    if not isinstance(parsed, dict):
        raise ValueError("OpenAPI YAML must be a mapping at top level")

    return parsed


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    try:
        loaded = _load_openapi_from_yaml(OPENAPI_YAML_PATH)
    except Exception:
        loaded = None

    if loaded is None:
        loaded = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

    app.openapi_schema = loaded
    return app.openapi_schema


app.openapi = custom_openapi
