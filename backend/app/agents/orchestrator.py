"""The central orchestrator: assigns work to agents, tracks execution, collects output.

Two execution modes, both real:
* `enqueue(...)` writes a Job row; the separate worker process picks it up. This is what
  the API uses, so a long render never blocks a request.
* `run_now(...)` executes inline in the current process. Used by tests and by the
  "run synchronously" flag, and it is the same code path the worker calls.

Retries are per task: transient failures go back to `queued` until `max_attempts`,
deterministic failures (bad input, wrong owner) fail immediately.
"""
from __future__ import annotations

from sqlalchemy import select

from app.agents.analytics import AnalyticsAgent
from app.agents.base import AgentContext, AgentError, NotAuthorised, finish_task
from app.agents.community import CommunityAgent
from app.agents.design import DesignAgent
from app.agents.editing import EditingAgent
from app.agents.seo import SEOAgent
from app.agents.video_intelligence import VideoIntelligenceAgent
from app.core.logging import get_logger
from app.models import AgentLog, AgentTask, Job
from app.models.base import utcnow

log = get_logger(__name__)

AGENT_CLASSES = {c.name: c for c in (
    VideoIntelligenceAgent, EditingAgent, DesignAgent, SEOAgent, AnalyticsAgent, CommunityAgent,
)}

MAX_ATTEMPTS = 3
PIPELINE_ORDER = ["video_intelligence", "editing", "design", "seo"]


def get_agent(name: str):
    cls = AGENT_CLASSES.get(name)
    if cls is None:
        raise AgentError(f"Unknown agent '{name}'. Available: {', '.join(AGENT_CLASSES)}")
    return cls()


def list_agents() -> list[dict]:
    return [cls().describe() for cls in AGENT_CLASSES.values()]


class Orchestrator:
    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id

    # --- task creation ---------------------------------------------------
    def create_task(self, agent: str, task_type: str, *, video_id: str | None = None,
                    clip_id: str | None = None, project_id: str | None = None,
                    params: dict | None = None) -> AgentTask:
        get_agent(agent)  # validate the name early
        task = AgentTask(
            user_id=self.user_id, agent=agent, task_type=task_type,
            video_id=video_id, clip_id=clip_id, project_id=project_id,
            input_data=params or {}, status="queued",
        )
        self.db.add(task)
        self.db.commit()
        return task

    def enqueue(self, agent: str, task_type: str, **kwargs) -> AgentTask:
        """Queue an agent task for the worker process."""
        task = self.create_task(agent, task_type, **kwargs)
        self.db.add(Job(kind="agent_task", payload={"task_id": task.id}))
        self.db.commit()
        return task

    def enqueue_pipeline(self, video_id: str, *, params: dict | None = None,
                         project_id: str | None = None) -> Job:
        """Queue the full analyse → cut → design → copy chain for one video."""
        job = Job(kind="pipeline", payload={"video_id": video_id,
                                            "params": params or {},
                                            "project_id": project_id})
        self.db.add(job)
        self.db.commit()
        return job

    # --- execution -------------------------------------------------------
    def execute(self, task: AgentTask) -> AgentTask:
        """Run one task in this process. Safe to call from the worker or from tests."""
        agent = get_agent(task.agent)
        task.status = "running"
        task.attempts += 1
        task.started_at = utcnow()
        self.db.commit()

        ctx = AgentContext(db=self.db, user_id=self.user_id, task=task,
                           params=dict(task.input_data or {}))
        try:
            ctx.log(f"{agent.title} agent started ({task.task_type})")
            output = agent.run(ctx)
            status = "awaiting_approval" if output.get("awaiting_approval") else "succeeded"
            finish_task(task, status=status, output=output)
            ctx.log(f"{agent.title} agent {status}")
        except (AgentError, NotAuthorised) as exc:
            # Deterministic failure: retrying the same input cannot help.
            finish_task(task, status="failed", error=str(exc))
            ctx.log(f"Failed: {exc}", "error")
        except Exception as exc:  # transient (disk, ffmpeg, db)
            log.exception("agent task failed")
            if task.attempts < MAX_ATTEMPTS:
                task.status = "queued"
                task.error = f"attempt {task.attempts} failed: {exc}"[:2000]
                ctx.log(f"Attempt {task.attempts} failed ({exc}); queued for retry", "warning")
            else:
                finish_task(task, status="failed", error=str(exc))
                ctx.log(f"Gave up after {task.attempts} attempts: {exc}", "error")
        self.db.commit()
        # Reload so the caller serialises the logs and output written during the run.
        self.db.refresh(task)
        return task

    def run_now(self, agent: str, task_type: str, **kwargs) -> AgentTask:
        task = self.create_task(agent, task_type, **kwargs)
        return self.execute(task)

    # --- the multi-agent chain -------------------------------------------
    def run_pipeline_now(self, video_id: str, *, params: dict | None = None,
                         project_id: str | None = None) -> dict:
        """Analyse, cut, design and write copy, in order, stopping at the first hard failure."""
        params = params or {}
        results: dict = {}
        video_task = self.run_now("video_intelligence", "analyse", video_id=video_id,
                                  project_id=project_id, params=params)
        results["video_intelligence"] = _summary(video_task)
        if video_task.status != "succeeded":
            return results

        platform = params.get("platform") or "youtube_shorts"
        edit_task = self.run_now("editing", "render_clips", video_id=video_id,
                                 project_id=project_id,
                                 params={**params, "platform": platform,
                                         "count": params.get("count", 3)})
        results["editing"] = _summary(edit_task)
        if edit_task.status != "succeeded":
            return results

        clip_ids = [c["clip_id"] for c in edit_task.output_data.get("clips", [])
                    if c.get("status") == "ready"]
        for cid in clip_ids[:3]:
            design = self.run_now("design", "thumbnails", video_id=video_id, clip_id=cid,
                                  project_id=project_id, params={"clip_id": cid})
            results[f"design:{cid}"] = _summary(design)
            seo = self.run_now("seo", "copy", video_id=video_id, clip_id=cid,
                               project_id=project_id, params={"clip_id": cid})
            results[f"seo:{cid}"] = _summary(seo)
        return results

    def approve(self, task: AgentTask, *, approve: bool, note: str = "") -> AgentTask:
        if task.status != "awaiting_approval":
            raise AgentError("This task is not waiting for approval.")
        task.status = "succeeded" if approve else "rejected"
        task.finished_at = utcnow()
        self.db.add(AgentLog(
            task_id=task.id, level="info",
            message=f"Human {'approved' if approve else 'rejected'} this draft. {note}".strip()))
        self.db.commit()
        return task


def _summary(task: AgentTask) -> dict:
    return {"task_id": task.id, "agent": task.agent, "status": task.status,
            "output": task.output_data, "error": task.error}


def execute_task_by_id(task_id: str) -> dict:
    """Worker entry point: open a session, run the task, return a small summary."""
    from app.core.database import session_scope
    with session_scope() as db:
        task = db.get(AgentTask, task_id)
        if task is None:
            return {"task_id": task_id, "status": "missing"}
        if task.status not in {"queued", "running"}:
            return {"task_id": task_id, "status": task.status, "skipped": True}
        Orchestrator(db, task.user_id).execute(task)
        return {"task_id": task.id, "status": task.status}


def run_pipeline_by_video(video_id: str, params: dict | None = None,
                          project_id: str | None = None) -> dict:
    from app.core.database import session_scope
    from app.models import Video
    with session_scope() as db:
        video = db.get(Video, video_id)
        if video is None:
            return {"error": "video not found"}
        return Orchestrator(db, video.user_id).run_pipeline_now(
            video_id, params=params, project_id=project_id)


def pending_tasks(db, user_id: str, limit: int = 20) -> list[AgentTask]:
    return list(db.scalars(
        select(AgentTask).where(AgentTask.user_id == user_id)
        .order_by(AgentTask.created_at.desc()).limit(limit)).all())
