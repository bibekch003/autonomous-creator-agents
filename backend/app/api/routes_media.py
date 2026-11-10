"""Media streaming: serve private files only to their owner.

Every route re-checks ownership before touching the filesystem, and the path is built
from a server-generated stored name — never from a client-supplied path.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Clip, Thumbnail, User, Video
from app.services import storage

router = APIRouter(tags=["media"])


@router.get("/videos/{video_id}/stream")
def stream_video(video_id: str, user: User = Depends(require_user),
                 db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None or v.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found.")
    path = storage.resolve_within(settings.uploads_dir, v.stored_name)
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "The stored file is missing.")
    # FileResponse handles HTTP Range, so the browser can scrub the timeline.
    return FileResponse(path, media_type=v.mime or "video/mp4", filename=v.original_name)


@router.get("/clips/{clip_id}/download")
def download_clip(clip_id: str, user: User = Depends(require_user),
                  db: Session = Depends(get_db)):
    c = db.get(Clip, clip_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found.")
    if not c.output_name:
        raise HTTPException(status.HTTP_409_CONFLICT, "This clip has not been rendered yet.")
    path = storage.resolve_within(settings.clips_dir, c.output_name)
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "The rendered file is missing.")
    nice = f"{(c.title or 'clip').replace(' ', '_')[:60]}_{c.platform}.mp4"
    return FileResponse(path, media_type="video/mp4", filename=nice)


@router.get("/clips/{clip_id}/subtitles")
def download_subtitles(clip_id: str, user: User = Depends(require_user),
                       db: Session = Depends(get_db)):
    c = db.get(Clip, clip_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found.")
    if not c.subtitle_name:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No subtitle file for this clip.")
    path = settings.temp_dir / c.subtitle_name
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "Subtitle file is no longer available.")
    return FileResponse(path, media_type="application/x-subrip",
                        filename=f"{(c.title or 'clip')[:40]}.srt")


@router.get("/thumbnails/{thumb_id}/image")
def thumbnail_image(thumb_id: str, user: User = Depends(require_user),
                    db: Session = Depends(get_db)):
    t = db.get(Thumbnail, thumb_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thumbnail not found.")
    path = storage.resolve_within(settings.thumbs_dir, t.stored_name)
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "The thumbnail file is missing.")
    return FileResponse(path, media_type="image/jpeg",
                        filename=f"thumbnail_{t.style}.jpg")
