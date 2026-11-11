"""Shared API dependencies: current user, session cookies, ownership guards."""
from __future__ import annotations

from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, new_session_token, token_fingerprint
from app.models import User, UserSession, UserSettings
from app.models.base import utcnow

COOKIE = settings.session_cookie
DEMO_EMAIL = "demo@creatoragents.dev"


def demo_user(db: Session) -> User:
    """One shared account for demo mode, recreated automatically if the DB resets."""
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        import secrets
        user = User(email=DEMO_EMAIL, name="Demo user",
                    password_hash=hash_password(secrets.token_urlsafe(24)))
        db.add(user)
        db.commit()
        db.refresh(user)
    if db.scalar(select(UserSettings).where(UserSettings.user_id == user.id)) is None:
        db.add(UserSettings(user_id=user.id))
        db.commit()
    return user


def _token_from(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE)
    return raw or None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Resolve the session cookie to a user. Returns None when absent or expired."""
    token = _token_from(request)
    if not token:
        # Demo mode: no cookie needed, every visitor shares one account.
        return demo_user(db) if settings.demo_mode else None
    session = db.scalar(select(UserSession).where(
        UserSession.token_hash == token_fingerprint(token)))
    if session is None or not session.is_valid:
        return demo_user(db) if settings.demo_mode else None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    return user


def start_session(db: Session, user: User, request: Request, response: Response) -> None:
    token = new_session_token()
    db.add(UserSession(
        user_id=user.id, token_hash=token_fingerprint(token),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        user_agent=(request.headers.get("user-agent") or "")[:250],
    ))
    user.last_login_at = utcnow()
    db.commit()
    response.set_cookie(
        COOKIE, token, httponly=True, samesite=settings.cookie_samesite,
        secure=settings.cookie_secure, max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def end_session(db: Session, request: Request, response: Response) -> None:
    token = _token_from(request)
    if token:
        session = db.scalar(select(UserSession).where(
            UserSession.token_hash == token_fingerprint(token)))
        if session:
            session.revoked = True
            db.commit()
    response.delete_cookie(COOKIE, path="/")


def ensure_settings(db: Session, user: User) -> UserSettings:
    row = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if row is None:
        row = UserSettings(user_id=user.id)
        db.add(row)
        db.commit()
    return row


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
