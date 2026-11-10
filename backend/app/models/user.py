"""User, session and settings models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, as_utc, new_id, utcnow


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    settings: Mapped["UserSettings | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False)
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan")


class UserSession(Base, TimestampMixin):
    """Server-side session. Stored by token hash so a DB leak cannot resume sessions."""

    __tablename__ = "user_sessions"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_session_token"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="")

    user: Mapped[User] = relationship(back_populates="sessions")

    @property
    def is_valid(self) -> bool:
        return not self.revoked and (as_utc(self.expires_at) or utcnow()) > utcnow()


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_settings_user"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    default_platform: Mapped[str] = mapped_column(String(40), default="youtube_shorts")
    default_clip_seconds: Mapped[int] = mapped_column(Integer, default=30)
    burn_captions: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_subtitles: Mapped[bool] = mapped_column(Boolean, default=True)
    creator_persona: Mapped[str] = mapped_column(
        Text, default="Direct, friendly, no hype. Explains the why before the how.")
    theme: Mapped[str] = mapped_column(String(20), default="dark")

    user: Mapped[User] = relationship(back_populates="settings")
