from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}
