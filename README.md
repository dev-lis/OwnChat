# OwnChat (API Gateway / Modular Monolith)

## Project Status

Current implementation is a **service-oriented modular monolith** on FastAPI:
- one deployable process (`uvicorn app.main:app`);
- service boundaries are split into modules (`auth`, `chats`, `messages`, `media`, `realtime`, `system`);
- in-memory storage is used for MVP behavior.

## Run

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Swagger / OpenAPI

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

OpenAPI loading behavior:
- App uses `docs/openapi.yaml` as primary schema source.
- If YAML is missing/invalid, app falls back to auto-generated OpenAPI.

## Current Code Structure

```text
app/
  main.py                  # entrypoint
  app_factory.py           # FastAPI app composition
  core/
    openapi.py             # OpenAPI loading and fallback
    time.py                # UTC timestamp helper
  state/
    store.py               # in-memory state
  system/
    router.py              # /health
  auth/
    models.py
    dependencies.py
    router.py
  chats/
    models.py
    router.py
  messages/
    models.py
    router.py
  media/
    models.py
    router.py
  realtime/
    router.py              # /ws/v1/connect
```

## Quick Smoke Test

### Temporary flow (login/password)

1. `POST /api/v1/auth/temp-register` with `login` and `password`.
2. If login is unique, API creates user and returns `access_token` + `refresh_token`.
3. If login already exists, API returns `409 conflict`.
4. Login rules: at least 3 chars, only letters and digits.

### OTP flow (legacy stub)

1. `POST /api/v1/auth/request-otp` with phone.
2. `POST /api/v1/auth/verify-otp` with returned `otp_session_id` and code `123456`.
3. `POST /api/v1/auth/register` with `verification_token`.
4. `POST /api/v1/auth/login` with `verification_token` and get `access_token`.
5. In Swagger click `Authorize` and set `Bearer <access_token>`.
