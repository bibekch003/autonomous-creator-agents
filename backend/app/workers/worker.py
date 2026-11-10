"""Background worker: claims queued jobs and runs them, one at a time.

    python -m app.workers.worker

Claims are atomic: `UPDATE jobs SET status='running' WHERE id=? AND status='queued'`
returns the rowcount, so two workers can never take the same job.
"""
from __future__ import annotations

import signal
import time

from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import session_scope
from app.core.logging import get_logger, setup_logging
from app.models import Job
from app.models.base import utcnow

log = get_logger(__name__)
_stopping = False


def _handle_stop(signum, _frame):  # pragma: no cover - signal path
    global _stopping
    _stopping = True
    log.info("Shutdown requested (signal %s); finishing the current job first.", signum)


def claim_next_job() -> dict | None:
    """Atomically take one queued job. Returns a plain dict so the session can close."""
    with session_scope() as db:
        candidate = db.scalar(
            select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1))
        if candidate is None:
            return None
        claimed = db.execute(
            update(Job)
            .where(Job.id == candidate.id, Job.status == "queued")
            .values(status="running", started_at=utcnow(), attempts=Job.attempts + 1)
        )
        if claimed.rowcount != 1:
            return None
        db.flush()
        return {"id": candidate.id, "kind": candidate.kind, "payload": dict(candidate.payload or {}),
                "attempts": candidate.attempts + 1, "max_attempts": candidate.max_attempts}


def run_job(job: dict) -> None:
    from app.agents.orchestrator import execute_task_by_id, run_pipeline_by_video

    kind, payload = job["kind"], job["payload"]
    if kind == "agent_task":
        result = execute_task_by_id(payload["task_id"])
        log.info("agent_task %s -> %s", payload.get("task_id"), result.get("status"))
        return
    if kind == "pipeline":
        result = run_pipeline_by_video(payload["video_id"], payload.get("params"),
                                       payload.get("project_id"))
        log.info("pipeline for video %s finished: %s",
                 payload.get("video_id"), list(result.keys()))
        return
    raise ValueError(f"Unknown job kind '{kind}'")


def _mark(job: dict, *, ok: bool, error: str = "") -> None:
    with session_scope() as db:
        row = db.get(Job, job["id"])
        if row is None:
            return
        if ok:
            row.status = "done"
            row.error = ""
        elif job["attempts"] < job["max_attempts"]:
            row.status = "queued"  # try again on the next loop
            row.error = error[:2000]
        else:
            row.status = "failed"
            row.error = error[:2000]
        row.finished_at = utcnow()


def run_once() -> bool:
    """Process a single job. Returns False when the queue was empty."""
    job = claim_next_job()
    if job is None:
        return False
    log.info("claimed %s job %s (attempt %s/%s)", job["kind"], job["id"],
             job["attempts"], job["max_attempts"])
    try:
        run_job(job)
        _mark(job, ok=True)
    except Exception as exc:  # noqa: BLE001 - the worker must survive any job
        log.exception("job %s failed", job["id"])
        _mark(job, ok=False, error=str(exc))
    return True


def main() -> None:  # pragma: no cover - long-running loop
    setup_logging()
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    log.info("worker started; polling every %.1fs", settings.job_poll_seconds)
    while not _stopping:
        worked = run_once()
        if not worked:
            time.sleep(settings.job_poll_seconds)
    log.info("worker stopped")


if __name__ == "__main__":  # pragma: no cover
    main()
