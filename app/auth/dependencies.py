from __future__ import annotations

from fastapi import Header, HTTPException

from app.state.store import ACCESS_TOKENS


def require_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Missing bearer token"})

    token = authorization.removeprefix("Bearer ").strip()
    user_id = ACCESS_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid token"})

    return user_id
