from __future__ import annotations

from pydantic import BaseModel, Field


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


class TempRegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)
