"""Clip routes: create (from a suggestion or your own timestamps), adjust, delete.

Rendering always goes through the Editing agent, so manual clips and suggested clips
share one code path — and one place where failures are recorded.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.api.deps import require_user
from app.api.routes_projects import owned_video
from app.core.config import PLATFORM_PRESETS, settings
from app.core.database import get_db
from app.models import Clip, GeneratedContent, Thumbnail, User, Video
from app.schemas.clip import ClipCreateIn, ClipOut, ClipUpdateIn
from app.services import storage

router = APIRouter(tags=["clips"])


def _clip_out(db: Session, c: Clip) -> ClipOut:
    data = ClipOut.model_validate(c)
    data.video_url = f"/api/clips/{c.id}/download" if c.status == "ready" else ""
    data.subtitle_url = f"/api/clips/{c.id}/subtitles" if c.subtitle_name else ""
    data.thumbnails = [{
        "id": t.id, "style": t.style, "headline": t.headline,
        "score": t.score.get("score") if isinstance(t.score, dict) else None,
        "image_url": f"/api/thumbnails/{t.id}/image",
    } for t in c.thumbnails]
    data.content = [{
        "id": g.id, "kind": g.kind, "platform": g.platform, "body": g.body,
        "source": g.source,
    } for g in c.content]
    return data


def owned_clip(db: Session, user: User, clip_id: str) -> Clip:
    c = db.get(Clip, clip_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found.")
    return c


@router.get("/videos/{video_id}/clips", response_model=list[ClipOut])
def list_clips(video_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    owned_video(db, user, video_id)
    rows = db.scalars(select(Clip).where(Clip.video_id == video_id)
                      .order_by(Clip.start_s)).all()
    return [_clip_out(db, c) for c in rows]


@router.post("/clips", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
def create_clip(payload: ClipCreateIn, sync: bool = Query(False),
                user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Render one clip for an explicit time range.

    `sync=true` renders immediately (used by tests and the CLI); otherwise a job is
    queued for the worker so the request returns instantly.
    """
    video = owned_video(db, user, payload.video_id)
    if payload.end_s <= payload.start_s:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "The end time must be after the start time.")
    length = payload.end_s - payload.start_s
    if length < settings.clip_min_seconds:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Clips must be at least {settings.clip_min_seconds:.0f} seconds.")
    if payload.end_s > video.duration_s + 0.5:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"That range runs past the end of the video ({video.duration_s:.1f}s).")
    if payload.platform not in PLATFORM_PRESETS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown platform preset.")

    orch = Orchestrator(db, user.id)
    params = {"platform": payload.platform,
              "clips": [{"start": payload.start_s, "end": payload.end_s,
                         "title": payload.title or "Custom clip",
                         "reason": payload.reason or "Chosen manually.",
                         "score": 0}]}
    if sync:
        task = orch.run_now("editing", "render_clip", video_id=video.id,
                            project_id=video.project_id, params=params)
        return {"task_id": task.id, "status": task.status,
                "output": task.output_data, "error": task.error}
    task = orch.enqueue("editing", "render_clip", video_id=video.id,
                        project_id=video.project_id, params=params)
    return {"task_id": task.id, "status": task.status,
            "note": "Queued. Poll the task or refresh the clip list."}


@router.get("/clips/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return _clip_out(db, owned_clip(db, user, clip_id))


@router.patch("/clips/{clip_id}", response_model=dict)
def update_clip(clip_id: str, payload: ClipUpdateIn, sync: bool = Query(False),
                user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Adjust timestamps or title, then re-render."""
    clip = owned_clip(db, user, clip_id)
    if payload.title is not None:
        clip.title = payload.title.strip()[:200]
    if payload.start_s is not None:
        clip.start_s = max(0.0, payload.start_s)
    if payload.end_s is not None:
        clip.end_s = payload.end_s
    if clip.end_s <= clip.start_s:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "The end time must be after the start time.")
    if payload.platform is not None:
        if payload.platform not in PLATFORM_PRESETS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown platform preset.")
        clip.platform = payload.platform
        clip.aspect = "vertical" if PLATFORM_PRESETS[payload.platform]["height"] > \
            PLATFORM_PRESETS[payload.platform]["width"] else "landscape"
    clip.status = "queued"
    db.commit()

    orch = Orchestrator(db, user.id)
    params = {"platform": clip.platform,
              "clips": [{"clip_id": clip.id, "start": clip.start_s, "end": clip.end_s,
                         "title": clip.title, "reason": clip.reason, "score": clip.score}]}
    task = (orch.run_now if sync else orch.enqueue)(
        "editing", "re_render", video_id=clip.video_id,
        clip_id=clip.id, project_id=clip.project_id, params=params)
    return {"task_id": task.id, "status": task.status, "clip": _clip_out(db, clip).model_dump()}


@router.delete("/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clip(clip_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    clip = owned_clip(db, user, clip_id)
    output = clip.output_name
    thumbs = [t.stored_name for t in clip.thumbnails]
    db.delete(clip)
    db.commit()
    storage.delete_project_files([], [output] if output else [], thumbs)
