"""Agent Control Centre routes: catalogue, tasks, run, approve, and the video pipeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import AgentError
from app.agents.orchestrator import Orchestrator, list_agents, pending_tasks
from app.api.deps import require_user
from app.api.routes_projects import owned_video
from app.core.database import get_db
from app.models import AgentTask, User
from app.schemas.agent import AgentInfo, AgentRunIn, ApprovalIn, TaskOut

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentInfo])
def catalogue(_: User = Depends(require_user)):
    return list_agents()


@router.get("/agents/tasks", response_model=list[TaskOut])
def tasks(limit: int = Query(20, ge=1, le=100), user: User = Depends(require_user),
          db: Session = Depends(get_db)):
    return [TaskOut.model_validate(t) for t in pending_tasks(db, user.id, limit)]


@router.get("/agents/tasks/{task_id}", response_model=TaskOut)
def task_detail(task_id: str, user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    t = db.get(AgentTask, task_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    return TaskOut.model_validate(t)


@router.post("/agents/run", response_model=TaskOut, status_code=status.HTTP_202_ACCEPTED)
def run_agent(payload: AgentRunIn, sync: bool = Query(True),
              user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Run one agent. Defaults to synchronous so the UI can show the result immediately."""
    orch = Orchestrator(db, user.id)
    try:
        if sync:
            task = orch.run_now(payload.agent, payload.agent, video_id=payload.video_id,
                                clip_id=payload.clip_id, project_id=payload.project_id,
                                params=payload.params)
        else:
            task = orch.enqueue(payload.agent, payload.agent, video_id=payload.video_id,
                                clip_id=payload.clip_id, project_id=payload.project_id,
                                params=payload.params)
    except AgentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return TaskOut.model_validate(task)


@router.post("/agents/tasks/{task_id}/approve", response_model=TaskOut)
def approve(task_id: str, payload: ApprovalIn, user: User = Depends(require_user),
            db: Session = Depends(get_db)):
    """Human approval gate. The Community agent can never publish on its own."""
    t = db.get(AgentTask, task_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    try:
        Orchestrator(db, user.id).approve(t, approve=payload.approve, note=payload.note)
    except AgentError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return TaskOut.model_validate(t)


# ---------------------------------------------------------------------------
# video pipeline
# ---------------------------------------------------------------------------
@router.post("/videos/{video_id}/analyse", response_model=dict,
             status_code=status.HTTP_202_ACCEPTED)
def analyse(video_id: str, sync: bool = Query(True), platform: str = Query("youtube_shorts"),
            clip_seconds: float = Query(30.0, ge=3, le=90),
            count: int = Query(3, ge=1, le=8),
            user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Video Intelligence only: probe, transcribe, find moments."""
    video = owned_video(db, user, video_id)
    orch = Orchestrator(db, user.id)
    params = {"clip_seconds": clip_seconds, "platform": platform, "count": count}
    if sync:
        task = orch.run_now("video_intelligence", "analyse", video_id=video.id,
                            project_id=video.project_id, params=params)
        return {"task_id": task.id, "status": task.status, "output": task.output_data,
                "error": task.error}
    task = orch.enqueue("video_intelligence", "analyse", video_id=video.id,
                        project_id=video.project_id, params=params)
    return {"task_id": task.id, "status": task.status, "note": "Queued for the worker."}


@router.post("/videos/{video_id}/pipeline", response_model=dict,
             status_code=status.HTTP_202_ACCEPTED)
def pipeline(video_id: str, sync: bool = Query(False), platform: str = Query("youtube_shorts"),
             clip_seconds: float = Query(30.0, ge=3, le=90),
             count: int = Query(3, ge=1, le=8),
             user: User = Depends(require_user), db: Session = Depends(get_db)):
    """The full chain: analyse → cut → thumbnails → copy.

    Queued by default so a long render never blocks the request. Pass sync=true to run
    inline (tests, CLI, or a small local file).
    """
    video = owned_video(db, user, video_id)
    orch = Orchestrator(db, user.id)
    params = {"clip_seconds": clip_seconds, "platform": platform, "count": count}
    if sync:
        results = orch.run_pipeline_now(video.id, params=params, project_id=video.project_id)
        ok = all(r.get("status") in {"succeeded", "awaiting_approval"} for r in results.values())
        return {"status": "succeeded" if ok else "partial", "results": results}
    job = orch.enqueue_pipeline(video.id, params=params, project_id=video.project_id)
    return {"job_id": job.id, "status": "queued",
            "note": "Queued. Start the worker (python -m app.workers.worker) to process it."}
