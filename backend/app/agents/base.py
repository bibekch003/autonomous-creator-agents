"""Agent base classes and the shared execution context.

Deliberately plain Python: an agent is a class with a `run` method that receives a
database session and returns a dict. No framework, no magic — easy to read, easy to
test, easy to replace with a queue later.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentLog, AgentTask, Clip, Project, Video
from app.models.base import utcnow


class AgentError(RuntimeError):
    """Raised when an agent cannot complete its work for a reportable reason."""


class NotAuthorised(AgentError):
    """Raised when the resource does not belong to the requesting user."""


@dataclass
class AgentContext:
    """Everything an agent is allowed to touch, plus its own logging surface."""
    db: Session
    user_id: str
    task: AgentTask
    params: dict = field(default_factory=dict)

    # --- logging ---------------------------------------------------------
    def log(self, message: str, level: str = "info") -> None:
        self.db.add(AgentLog(task_id=self.task.id, level=level, message=str(message)[:2000]))
        self.db.commit()

    def progress(self, pct: int) -> None:
        self.task.progress = max(0, min(100, int(pct)))
        self.db.commit()

    # --- ownership-checked loaders --------------------------------------
    def video(self, video_id: str | None = None) -> Video:
        vid = video_id or self.params.get("video_id") or self.task.video_id
        if not vid:
            raise AgentError("No video specified for this task.")
        obj = self.db.get(Video, vid)
        if obj is None:
            raise AgentError(f"Video {vid} not found.")
        if obj.user_id != self.user_id:
            raise NotAuthorised("That video belongs to another account.")
        return obj

    def clip(self, clip_id: str | None = None) -> Clip:
        cid = clip_id or self.params.get("clip_id") or self.task.clip_id
        if not cid:
            raise AgentError("No clip specified for this task.")
        obj = self.db.get(Clip, cid)
        if obj is None:
            raise AgentError(f"Clip {cid} not found.")
        if obj.user_id != self.user_id:
            raise NotAuthorised("That clip belongs to another account.")
        return obj

    def project(self, project_id: str | None = None) -> Project:
        pid = project_id or self.params.get("project_id") or self.task.project_id
        if not pid:
            raise AgentError("No project specified for this task.")
        obj = self.db.get(Project, pid)
        if obj is None:
            raise AgentError(f"Project {pid} not found.")
        if obj.user_id != self.user_id:
            raise NotAuthorised("That project belongs to another account.")
        return obj

    def user_clips(self) -> list[Clip]:
        return list(self.db.scalars(select(Clip).where(Clip.user_id == self.user_id)).all())


class BaseAgent(ABC):
    """Contract every agent implements."""
    name: str = "base"
    title: str = "Base agent"
    description: str = ""
    capabilities: list[str] = []
    requires_approval: bool = False

    @abstractmethod
    def run(self, ctx: AgentContext) -> dict:
        """Do the work and return a JSON-serialisable result."""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "requires_approval": self.requires_approval,
        }


def finish_task(task: AgentTask, *, status: str, output: dict | None = None,
                error: str = "") -> None:
    task.status = status
    task.output_data = output or {}
    task.error = error[:4000]
    task.progress = 100 if status in {"succeeded", "failed", "rejected"} else task.progress
    task.finished_at = utcnow()
