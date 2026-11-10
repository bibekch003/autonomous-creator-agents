"""Agent task and analytics schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    level: str
    message: str
    created_at: datetime


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    agent: str
    task_type: str
    status: str
    progress: int
    attempts: int
    error: str
    input_data: dict = {}
    output_data: dict = {}
    video_id: str | None = None
    clip_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    logs: list[LogOut] = []


class AgentInfo(BaseModel):
    name: str
    title: str
    description: str
    capabilities: list[str]
    requires_approval: bool


class AgentRunIn(BaseModel):
    agent: str
    video_id: str | None = None
    clip_id: str | None = None
    project_id: str | None = None
    params: dict = {}


class ApprovalIn(BaseModel):
    approve: bool
    note: str = ""


class AnalyticsOverview(BaseModel):
    projects: int
    videos: int
    videos_processed: int
    clips: int
    clips_ready: int
    thumbnails: int
    total_video_seconds: float
    total_clip_seconds: float
    tasks_succeeded: int
    tasks_failed: int
    storage_mb: float
    # Explicitly local application statistics, not imported platform analytics.
    source_note: str = (
        "These are locally generated application statistics from your own projects. "
        "No platform analytics have been imported."
    )


class TimelinePoint(BaseModel):
    label: str
    value: float


class AnalyticsDetail(AnalyticsOverview):
    activity: list[TimelinePoint] = []
    by_platform: list[TimelinePoint] = []
    recent: list[dict] = []
