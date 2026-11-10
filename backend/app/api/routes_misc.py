"""Analytics routes (local application statistics) and user settings."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import ensure_settings, require_user
from app.core.database import get_db
from app.models import User
from app.schemas.agent import AnalyticsDetail, AnalyticsOverview
from app.schemas.auth import SettingsIn, SettingsOut
from app.services import analytics as analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview", response_model=AnalyticsOverview)
def overview(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return analytics_service.overview(db, user.id)


@router.get("/analytics/detail", response_model=AnalyticsDetail)
def detail(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return analytics_service.detail(db, user.id)


@router.get("/settings", response_model=SettingsOut)
def get_settings_route(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return SettingsOut.model_validate(ensure_settings(db, user))


@router.patch("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsIn, user: User = Depends(require_user),
                    db: Session = Depends(get_db)):
    row = ensure_settings(db, user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    db.commit()
    return SettingsOut.model_validate(row)
