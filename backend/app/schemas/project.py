"""Project, video and transcript schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    status: str
    created_at: datetime
    video_count: int = 0
    clip_count: int = 0


class MomentOut(BaseModel):
    start: float
    end: float
    score: float
    reason: str
    label: str = ""


class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source: str
    language: str
    text: str
    cues: list[dict] = []


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    original_name: str
    size_bytes: int
    duration_s: float
    width: int
    height: int
    fps: float
    has_audio: bool
    status: str
    error: str
    moments: list[dict] = []
    created_at: datetime
    clip_count: int = 0
    stream_url: str = ""


class VideoDetailOut(VideoOut):
    transcript: TranscriptOut | None = None
    analysis: dict = {}


class TranscriptIn(BaseModel):
    """Paste a transcript when ASR is unavailable or you want exact wording."""
    text: str = Field(min_length=1, max_length=200_000)
    language: str = Field(default="en", max_length=12)
