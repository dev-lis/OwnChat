from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def _load_openapi_from_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        parsed = yaml.safe_load(file)

    if not isinstance(parsed, dict):
        raise ValueError("OpenAPI YAML must be a mapping at top level")

    return parsed


def configure_openapi(app: FastAPI, openapi_yaml_path: Path) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        try:
            loaded = _load_openapi_from_yaml(openapi_yaml_path)
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
