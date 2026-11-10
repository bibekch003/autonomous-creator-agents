"""Agent task/log models and the background job queue."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (JSON, DateTime, ForeignKey, Index, Integer, String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_id

TASK_STATUS = ("queued", "running", "succeeded", "failed", "awaiting_approval", "rejected")
AGENT_NAMES = ("video_intelligence", "editing", "design", "seo", "analytics", "community")


class AgentTask(Base, TimestampMixin):
    __tablename__ = "agent_tasks"
    __table_args__ = (Index("ix_tasks_user_status", "user_id", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    clip_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("clips.id", ondelete="SET NULL"))

    agent: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    logs: Mapped[list["AgentLog"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="AgentLog.created_at")


class AgentLog(Base, TimestampMixin):
    __tablename__ = "agent_logs"
    __table_args__ = (Index("ix_logs_task", "task_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[str] = mapped_column(String(10), default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped[AgentTask] = relationship(back_populates="logs")


class Job(Base, TimestampMixin):
    """DB-backed queue so long video work never blocks an API request.

    A separate worker process (`python -m app.workers.worker`) claims jobs with a
    conditional UPDATE, which keeps the claim atomic without Redis.
    """

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
