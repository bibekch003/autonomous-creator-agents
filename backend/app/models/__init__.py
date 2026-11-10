"""Model package: importing this registers every mapper with SQLAlchemy."""
from app.models.agent import AgentLog, AgentTask, Job
from app.models.base import TimestampMixin, new_id, utcnow
from app.models.content import Clip, GeneratedContent, Project, Thumbnail, Transcript, Video
from app.models.user import User, UserSession, UserSettings

__all__ = [
    "AgentLog", "AgentTask", "Job", "TimestampMixin", "new_id", "utcnow",
    "Clip", "GeneratedContent", "Project", "Thumbnail", "Transcript", "Video",
    "User", "UserSession", "UserSettings",
]
