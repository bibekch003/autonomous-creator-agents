"""Thumbnail Studio routes: render concepts, upload your own, list and delete."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.api.deps import require_user
from app.api.routes_projects import owned_video
from app.core.config import settings
from app.core.database import get_db
from app.models import Thumbnail, User
from app.schemas.clip import ThumbnailOut, ThumbnailRenderIn
from app.services import storage, thumbnail_service

router = APIRouter(prefix="/thumbnails", tags=["thumbnails"])


def _out(t: Thumbnail) -> ThumbnailOut:
    data = ThumbnailOut.model_validate(t)
    data.image_url = f"/api/thumbnails/{t.id}/image"
    return data


@router.post("/render", response_model=list[ThumbnailOut])
def render(payload: ThumbnailRenderIn, user: User = Depends(require_user),
           db: Session = Depends(get_db)):
    """Render one concept per style. Runs the Design agent synchronously (fast, CPU only)."""
    video = owned_video(db, user, payload.video_id)
    task = Orchestrator(db, user.id).run_now(
        "design", "thumbnails", video_id=video.id, clip_id=payload.clip_id,
        project_id=video.project_id,
        params={"clip_id": payload.clip_id, "headline": payload.headline,
                "styles": payload.styles, "at_seconds": payload.at_seconds})
    if task.status != "succeeded":
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            task.error or "Thumbnail rendering failed.")
    ids = [t["thumbnail_id"] for t in task.output_data.get("thumbnails", [])]
    rows = db.scalars(select(Thumbnail).where(Thumbnail.id.in_(ids))).all()
    return [_out(t) for t in rows]


@router.post("/upload", response_model=ThumbnailOut, status_code=status.HTTP_201_CREATED)
def upload_thumbnail(file: UploadFile = File(...), video_id: str = Form(...),
                     clip_id: str = Form(""), headline: str = Form(""),
                     user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Attach your own image as a thumbnail option."""
    video = owned_video(db, user, video_id)
    try:
        ext = storage.validate_image_upload(file.filename or "", file.size or 0)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    stored = storage.new_stored_name(ext)
    dest = settings.thumbs_dir / stored
    try:
        storage.save_stream(file.file, dest, 20 * 1024 * 1024)
    except ValueError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc

    check = thumbnail_service.validate_custom_image(dest)
    if not check["ok"]:
        storage.safe_delete(dest)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, check["warning"])

    row = Thumbnail(video_id=video.id, clip_id=clip_id or None, user_id=user.id,
                    headline=headline[:120] or "Uploaded image", style="custom",
                    width=check["width"], height=check["height"],
                    stored_name=stored, is_uploaded=True,
                    score={"score": None, "reasons": ["Uploaded by you; not scored."]})
    db.add(row)
    db.commit()
    return _out(row)


@router.get("", response_model=list[ThumbnailOut])
def list_thumbnails(clip_id: str | None = None, video_id: str | None = None,
                    user: User = Depends(require_user), db: Session = Depends(get_db)):
    stmt = select(Thumbnail).where(Thumbnail.user_id == user.id)
    if clip_id:
        stmt = stmt.where(Thumbnail.clip_id == clip_id)
    if video_id:
        stmt = stmt.where(Thumbnail.video_id == video_id)
    rows = db.scalars(stmt.order_by(Thumbnail.created_at.desc())).all()
    return [_out(t) for t in rows]


@router.delete("/{thumb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thumbnail(thumb_id: str, user: User = Depends(require_user),
                     db: Session = Depends(get_db)):
    row = db.get(Thumbnail, thumb_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thumbnail not found.")
    stored = row.stored_name
    db.delete(row)
    db.commit()
    storage.safe_delete(settings.thumbs_dir / stored)
