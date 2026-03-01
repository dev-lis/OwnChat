# OwnChat (API Gateway)

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Swagger / OpenAPI

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

`app/main.py` loads OpenAPI schema from `docs/openapi.yaml`.
If the YAML file is missing or invalid, FastAPI falls back to auto-generated schema.

## Quick smoke test (stubs)

1. `POST /api/v1/auth/request-otp` with phone.
2. `POST /api/v1/auth/verify-otp` with returned `otp_session_id` and code `123456`.
3. `POST /api/v1/auth/register` with `verification_token`.
4. `POST /api/v1/auth/login` with `verification_token` and get `access_token`.
5. In Swagger click `Authorize` and set `Bearer <access_token>`.
