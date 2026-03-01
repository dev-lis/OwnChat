from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.time import now_iso
from app.state.store import ACCESS_TOKENS

router = APIRouter(tags=["Realtime"])


@router.websocket("/ws/v1/connect")
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
