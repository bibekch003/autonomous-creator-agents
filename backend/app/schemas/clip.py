"""Clip, generated content and thumbnail schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClipCreateIn(BaseModel):
    """Either accept a suggested moment, or specify your own timestamps."""
    video_id: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    title: str = Field(default="", max_length=200)
    platform: str = Field(default="youtube_shorts", max_length=40)
    reason: str = Field(default="", max_length=500)


class ClipUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    start_s: float | None = Field(default=None, ge=0)
    end_s: float | None = Field(default=None, gt=0)
    platform: str | None = Field(default=None, max_length=40)


class ClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    video_id: str
    project_id: str
    title: str
    start_s: float
    end_s: float
    duration_s: float
    aspect: str
    platform: str
    status: str
    file_size: int
    has_subtitles: bool
    error: str
    reason: str
    score: float
    created_at: datetime
    video_url: str = ""
    subtitle_url: str = ""
    # Populated explicitly in the route from the ORM relationships.
    thumbnails: list[Any] = []
    content: list[Any] = []


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    clip_id: str | None
    kind: str
    platform: str
    body: str
    is_selected: bool
    source: str


class SeoIn(BaseModel):
    clip_id: str | None = None
    video_id: str | None = None
    platform: str = Field(default="youtube_shorts", max_length=40)
    topic: str = Field(default="", max_length=200)


class ThumbnailRenderIn(BaseModel):
    video_id: str
    clip_id: str | None = None
    headline: str = Field(default="", max_length=120)
    styles: list[str] = Field(default_factory=lambda: ["bold_lower", "split_band", "top_strip"])
    at_seconds: float = Field(default=0.0, ge=0)


class ThumbnailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    clip_id: str | None
    video_id: str
    headline: str
    style: str
    width: int
    height: int
    is_uploaded: bool
    score: dict = {}
    created_at: datetime
    image_url: str = ""
