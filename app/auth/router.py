from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.auth.models import LoginRequest, RefreshRequest, RegisterRequest, RequestOtpRequest, TempRegisterRequest, VerifyOtpRequest
from app.core.time import now_iso
from app.state.store import ACCESS_TOKENS, LOGIN_RE, OTP_SESSIONS, REFRESH_TOKENS, USERS_BY_LOGIN, USERS_BY_PHONE, VERIFICATION_TOKENS

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/request-otp")
def request_otp(body: RequestOtpRequest) -> dict[str, Any]:
    otp_session_id = str(uuid4())
    OTP_SESSIONS[otp_session_id] = {"phone": body.phone, "code": "123456", "verified": False, "created_at": now_iso()}
    return {"otp_session_id": otp_session_id, "expires_in": 300}


@router.post("/verify-otp")
def verify_otp(body: VerifyOtpRequest) -> dict[str, Any]:
    session = OTP_SESSIONS.get(body.otp_session_id)
    if not session or body.code != session["code"]:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid OTP"})

    session["verified"] = True
    verification_token = str(uuid4())
    VERIFICATION_TOKENS[verification_token] = session["phone"]
    return {"verified": True, "verification_token": verification_token}


@router.post("/register", status_code=201)
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


@router.post("/login")
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


@router.post("/refresh")
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


@router.post("/temp-register", status_code=201)
def temp_register(body: TempRegisterRequest) -> dict[str, Any]:
    if not LOGIN_RE.fullmatch(body.login):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_request",
                "message": "Login must be at least 3 characters and contain only letters and digits",
            },
        )
    if body.login in USERS_BY_LOGIN:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "User with this login already exists"})

    user_id = str(uuid4())
    created_at = now_iso()
    USERS_BY_LOGIN[body.login] = {
        "user_id": user_id,
        "login": body.login,
        "password": body.password,
        "created_at": created_at,
    }

    access_token = str(uuid4())
    refresh_token = str(uuid4())
    ACCESS_TOKENS[access_token] = user_id
    REFRESH_TOKENS[refresh_token] = user_id
    return {
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "created_at": created_at,
    }
