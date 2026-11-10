"""Auth and user schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128,
                          description="At least 8 characters.")


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: EmailStr
    created_at: datetime


class SettingsIn(BaseModel):
    default_platform: str | None = Field(default=None, max_length=40)
    default_clip_seconds: int | None = Field(default=None, ge=5, le=90)
    burn_captions: bool | None = None
    auto_subtitles: bool | None = None
    creator_persona: str | None = Field(default=None, max_length=500)
    theme: str | None = Field(default=None, max_length=20)


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    default_platform: str
    default_clip_seconds: int
    burn_captions: bool
    auto_subtitles: bool
    creator_persona: str
    theme: str


class AuthOut(BaseModel):
    user: UserOut
    settings: SettingsOut | None = None
