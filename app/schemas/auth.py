from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    full_name: str | None = Field(default=None, max_length=200)
    timezone: str = Field(default="UTC", max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    device_id: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str
    device_id: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=256)


class LogoutIn(BaseModel):
    device_id: str


class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str
    request_id: str
