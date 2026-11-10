"""Generated content (titles, descriptions, hashtags, captions) and SEO runs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.api.deps import require_user
from app.api.routes_projects import owned_video
from app.core.database import get_db
from app.models import Clip, GeneratedContent, Project, User
from app.schemas.clip import ContentOut, SeoIn

router = APIRouter(tags=["content"])


@router.post("/content/generate", response_model=dict)
def generate(payload: SeoIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Run the SEO agent now. Fast (no video work), so it is synchronous by design."""
    if not payload.clip_id and not payload.video_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Provide a clip_id or a video_id.")
    video_id = payload.video_id
    project_id = None
    if payload.clip_id:
        clip = db.get(Clip, payload.clip_id)
        if clip is None or clip.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found.")
        video_id, project_id = clip.video_id, clip.project_id
    else:
        video = owned_video(db, user, video_id)
        project_id = video.project_id

    task = Orchestrator(db, user.id).run_now(
        "seo", "copy", video_id=video_id, clip_id=payload.clip_id, project_id=project_id,
        params={"clip_id": payload.clip_id, "platform": payload.platform,
                "topic": payload.topic})
    if task.status != "succeeded":
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            task.error or "The copy engine could not complete.")
    return {"task_id": task.id, **task.output_data}


@router.get("/content", response_model=list[ContentOut])
def list_content(clip_id: str | None = None, video_id: str | None = None,
                 user: User = Depends(require_user), db: Session = Depends(get_db)):
    stmt = select(GeneratedContent).where(GeneratedContent.project_id.in_(
        select(Project.id).where(Project.user_id == user.id)))
    if clip_id:
        stmt = stmt.where(GeneratedContent.clip_id == clip_id)
    elif video_id:
        stmt = stmt.where(GeneratedContent.clip_id.in_(
            select(Clip.id).where(Clip.video_id == video_id)))
    rows = db.scalars(stmt.order_by(GeneratedContent.kind, GeneratedContent.created_at)).all()
    return [ContentOut.model_validate(r) for r in rows]


@router.patch("/content/{content_id}/select", response_model=ContentOut)
def select_content(content_id: str, user: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    """Mark one option as chosen (titles are a set of alternatives)."""
    row = db.get(GeneratedContent, content_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found.")
    project = db.get(Project, row.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found.")
    siblings = db.scalars(select(GeneratedContent).where(
        GeneratedContent.clip_id == row.clip_id,
        GeneratedContent.kind == row.kind)).all()
    for s in siblings:
        s.is_selected = False
    row.is_selected = True
    db.commit()
    return ContentOut.model_validate(row)


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(content_id: str, user: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    row = db.get(GeneratedContent, content_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found.")
    project = db.get(Project, row.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found.")
    db.delete(row)
    db.commit()
