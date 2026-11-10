"""Project and video routes: create projects, upload videos, list and inspect."""
from __future__ import annotations

from pathlib import Path

from fastapi import (APIRouter, Depends, File, HTTPException, Query, UploadFile, status)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Clip, Project, Transcript, User, Video
from app.schemas.project import (ProjectIn, ProjectOut, TranscriptIn, VideoDetailOut,
                                 VideoOut)
from app.services import storage
from app.services.video import media

router = APIRouter(tags=["projects"])


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------
def _project_out(db: Session, p: Project) -> ProjectOut:
    videos = int(db.scalar(select(func.count()).select_from(Video)
                           .where(Video.project_id == p.id)) or 0)
    clips = int(db.scalar(select(func.count()).select_from(Clip)
                          .where(Clip.project_id == p.id)) or 0)
    data = ProjectOut.model_validate(p)
    data.video_count, data.clip_count = videos, clips
    return data


def owned_project(db: Session, user: User, project_id: str) -> Project:
    p = db.get(Project, project_id)
    if p is None or p.user_id != user.id:
        # 404 rather than 403: do not confirm that someone else's project exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    return p


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).where(Project.user_id == user.id)
                      .order_by(Project.created_at.desc())).all()
    return [_project_out(db, p) for p in rows]


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectIn, user: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    p = Project(user_id=user.id, name=payload.name.strip(), description=payload.description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_out(db, p)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    return _project_out(db, owned_project(db, user, project_id))


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectIn, user: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    p = owned_project(db, user, project_id)
    p.name = payload.name.strip()
    p.description = payload.description
    db.commit()
    return _project_out(db, p)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    p = owned_project(db, user, project_id)
    video_files = [v.stored_name for v in p.videos]
    clip_files = [c.output_name for c in db.scalars(
        select(Clip).where(Clip.project_id == p.id)).all() if c.output_name]
    thumb_files = [t.stored_name for v in p.videos for c in v.clips for t in c.thumbnails]
    db.delete(p)
    db.commit()
    storage.delete_project_files(video_files, clip_files, thumb_files)


# ---------------------------------------------------------------------------
# videos
# ---------------------------------------------------------------------------
def _video_out(db: Session, v: Video) -> VideoOut:
    data = VideoOut.model_validate(v)
    data.clip_count = int(db.scalar(select(func.count()).select_from(Clip)
                                    .where(Clip.video_id == v.id)) or 0)
    data.stream_url = f"/api/videos/{v.id}/stream"
    return data


def owned_video(db: Session, user: User, video_id: str) -> Video:
    v = db.get(Video, video_id)
    if v is None or v.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found.")
    return v


@router.get("/projects/{project_id}/videos", response_model=list[VideoOut])
def list_videos(project_id: str, user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    owned_project(db, user, project_id)
    rows = db.scalars(select(Video).where(Video.project_id == project_id)
                      .order_by(Video.created_at.desc())).all()
    return [_video_out(db, v) for v in rows]


@router.post("/projects/{project_id}/videos", response_model=VideoOut,
             status_code=status.HTTP_201_CREATED)
def upload_video(project_id: str, file: UploadFile = File(...),
                 user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Validate, stream to disk, probe, and create the video record.

    The file is written under a server-generated name, so user input never reaches the
    filesystem path. Size is enforced while streaming, not after.
    """
    owned_project(db, user, project_id)
    try:
        ext = storage.validate_video_upload(file.filename or "", file.size or 0)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    stored = storage.new_stored_name(ext)
    dest = settings.uploads_dir / stored
    try:
        written = storage.save_stream(file.file, dest,
                                      settings.max_upload_mb * 1024 * 1024)
    except ValueError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc

    video = Video(
        project_id=project_id, user_id=user.id,
        original_name=storage.clean_filename(file.filename or stored),
        stored_name=stored, mime=file.content_type or "video/mp4", size_bytes=written,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Probe immediately so the UI can show duration and dimensions.
    try:
        meta = media.probe(dest)
        video.duration_s = meta["duration"]
        video.width, video.height = meta["width"], meta["height"]
        video.fps = meta["fps"]
        video.has_audio = meta["has_audio"]
        db.commit()
    except Exception as exc:
        video.status = "failed"
        video.error = f"Could not read this file as video: {exc}"[:500]
        db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, video.error) from exc

    db.refresh(video)
    return _video_out(db, video)


@router.get("/videos/{video_id}", response_model=VideoDetailOut)
def get_video(video_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    v = owned_video(db, user, video_id)
    data = VideoDetailOut.model_validate(v)
    data.clip_count = int(db.scalar(select(func.count()).select_from(Clip)
                                    .where(Clip.video_id == v.id)) or 0)
    data.stream_url = f"/api/videos/{v.id}/stream"
    tr = db.scalar(select(Transcript).where(Transcript.video_id == v.id))
    data.transcript = tr
    return data


@router.post("/videos/{video_id}/transcript", response_model=VideoDetailOut)
def set_transcript(video_id: str, payload: TranscriptIn,
                   user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Paste a transcript when ASR is unavailable. Marked source='manual'."""
    v = owned_video(db, user, video_id)
    tr = db.scalar(select(Transcript).where(Transcript.video_id == v.id))
    if tr is None:
        tr = Transcript(video_id=v.id)
        db.add(tr)
    tr.text = payload.text.strip()
    tr.language = payload.language
    tr.source = "manual"
    db.commit()
    return get_video(video_id, user, db)


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: str, user: User = Depends(require_user),
                 db: Session = Depends(get_db)):
    v = owned_video(db, user, video_id)
    clips = db.scalars(select(Clip).where(Clip.video_id == v.id)).all()
    clip_files = [c.output_name for c in clips if c.output_name]
    thumb_files = [t.stored_name for c in clips for t in c.thumbnails]
    stored = v.stored_name
    db.delete(v)
    db.commit()
    storage.delete_project_files([stored], clip_files, thumb_files)
