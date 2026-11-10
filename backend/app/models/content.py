"""Project, video, transcript, clip, generated content and thumbnail models."""
from __future__ import annotations

from sqlalchemy import (JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_id

VIDEO_STATUS = ("uploaded", "analysing", "ready", "failed")
CLIP_STATUS = ("queued", "rendering", "ready", "failed")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")

    user: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    videos: Mapped[list["Video"]] = relationship(
        back_populates="project", cascade="all, delete-orphan")
    clips: Mapped[list["Clip"]] = relationship(
        back_populates="project", cascade="all, delete-orphan")


class Video(Base, TimestampMixin):
    __tablename__ = "videos"
    __table_args__ = (Index("ix_videos_project", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    mime: Mapped[str] = mapped_column(String(80), default="video/mp4")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    duration_s: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    has_audio: Mapped[bool] = mapped_column(Boolean, default=True)

    status: Mapped[str] = mapped_column(String(20), default="uploaded", index=True)
    error: Mapped[str] = mapped_column(Text, default="")
    # Interesting moments and the audio analysis live here as JSON: they are derived
    # data, always regenerated from the file, and never queried relationally.
    moments: Mapped[list] = mapped_column(JSON, default=list)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="videos")
    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="video", cascade="all, delete-orphan", uselist=False)
    clips: Mapped[list["Clip"]] = relationship(
        back_populates="video", cascade="all, delete-orphan")


class Transcript(Base, TimestampMixin):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    video_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="demo")  # whisper|manual|demo
    language: Mapped[str] = mapped_column(String(12), default="en")
    text: Mapped[str] = mapped_column(Text, default="")
    cues: Mapped[list] = mapped_column(JSON, default=list)  # [{start,end,text}]

    video: Mapped[Video] = relationship(back_populates="transcript")


class Clip(Base, TimestampMixin):
    __tablename__ = "clips"
    __table_args__ = (Index("ix_clips_video", "video_id", "start_s"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    video_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(200), default="")
    start_s: Mapped[float] = mapped_column(Float, nullable=False)
    end_s: Mapped[float] = mapped_column(Float, nullable=False)
    aspect: Mapped[str] = mapped_column(String(16), default="vertical")
    platform: Mapped[str] = mapped_column(String(40), default="youtube_shorts")

    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    output_name: Mapped[str] = mapped_column(String(160), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    subtitle_name: Mapped[str] = mapped_column(String(160), default="")
    has_subtitles: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str] = mapped_column(Text, default="")

    reason: Mapped[str] = mapped_column(Text, default="")   # why this moment was suggested
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100, from measured signals

    video: Mapped[Video] = relationship(back_populates="clips")
    project: Mapped[Project] = relationship(back_populates="clips")
    thumbnails: Mapped[list["Thumbnail"]] = relationship(
        back_populates="clip", cascade="all, delete-orphan")
    content: Mapped[list["GeneratedContent"]] = relationship(
        back_populates="clip", cascade="all, delete-orphan")

    @property
    def duration_s(self) -> float:
        return round(max(0.0, self.end_s - self.start_s), 2)


class GeneratedContent(Base, TimestampMixin):
    __tablename__ = "generated_content"
    __table_args__ = (Index("ix_content_clip_kind", "clip_id", "kind"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    clip_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("clips.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # title|description|hashtags|caption|platform_text
    platform: Mapped[str] = mapped_column(String(40), default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="offline")  # offline|llm

    clip: Mapped[Clip | None] = relationship(back_populates="content")


class Thumbnail(Base, TimestampMixin):
    __tablename__ = "thumbnails"
    __table_args__ = (Index("ix_thumbs_clip", "clip_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    clip_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("clips.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    headline: Mapped[str] = mapped_column(String(120), default="")
    style: Mapped[str] = mapped_column(String(30), default="bold_lower")
    width: Mapped[int] = mapped_column(Integer, default=1080)
    height: Mapped[int] = mapped_column(Integer, default=1920)
    stored_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[dict] = mapped_column(JSON, default=dict)

    clip: Mapped[Clip | None] = relationship(back_populates="thumbnails")
