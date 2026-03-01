from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_user_id
from app.core.time import now_iso
from app.media.models import CreateUploadRequest
from app.state.store import ATTACHMENTS

router = APIRouter(prefix="/api/v1/media", tags=["Media"])


@router.post("/uploads", status_code=201)
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
