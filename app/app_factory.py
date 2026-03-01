from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.chats.router import router as chats_router
from app.core.openapi import configure_openapi
from app.media.router import router as media_router
from app.messages.router import router as messages_router
from app.realtime.router import router as realtime_router
from app.system.router import router as system_router

BASE_DIR = Path(__file__).resolve().parent.parent
OPENAPI_YAML_PATH = BASE_DIR / "docs" / "openapi.yaml"


def create_app() -> FastAPI:
    app = FastAPI(
        title="OwnChat API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(chats_router)
    app.include_router(messages_router)
    app.include_router(media_router)
    app.include_router(realtime_router)

    configure_openapi(app, OPENAPI_YAML_PATH)
    return app
