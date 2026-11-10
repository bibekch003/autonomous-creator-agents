"""Authentication routes: register, login, logout, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (client_ip, end_session, ensure_settings, get_current_user,
                          require_user, start_session)
from app.core.database import get_db
from app.core.security import (hash_password, rate_limit_hit, rate_limit_reset,
                               verify_password)
from app.models import User
from app.schemas.auth import AuthOut, LoginIn, RegisterIn, SettingsOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, request: Request, response: Response,
             db: Session = Depends(get_db)) -> AuthOut:
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")
    try:
        pw_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    user = User(email=email, name=payload.name.strip(), password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    row = ensure_settings(db, user)
    start_session(db, user, request, response)
    return AuthOut(user=UserOut.model_validate(user), settings=SettingsOut.model_validate(row))


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, response: Response,
          db: Session = Depends(get_db)) -> AuthOut:
    ip = client_ip(request)
    if rate_limit_hit(f"login:{ip}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many sign-in attempts. Wait a few minutes and try again.")

    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    # Same error for unknown email and wrong password: no account enumeration.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")

    rate_limit_reset(f"login:{ip}")
    row = ensure_settings(db, user)
    start_session(db, user, request, response)
    return AuthOut(user=UserOut.model_validate(user), settings=SettingsOut.model_validate(row))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    end_session(db, request, response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthOut)
def me(user: User = Depends(require_user), db: Session = Depends(get_db)) -> AuthOut:
    row = ensure_settings(db, user)
    return AuthOut(user=UserOut.model_validate(user), settings=SettingsOut.model_validate(row))


@router.get("/session", include_in_schema=False)
def session_state(user: User | None = Depends(get_current_user)) -> dict:
    """Lightweight probe the frontend uses to decide between login and dashboard."""
    return {"authenticated": user is not None,
            "user": UserOut.model_validate(user).model_dump() if user else None}
