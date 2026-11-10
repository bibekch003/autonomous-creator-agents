"""Application settings, resolved from the environment with sane local defaults.

Everything is overridable with `ACA_`-prefixed environment variables or a `.env` file,
so the same code runs on a laptop with SQLite and local disk, and in Docker against
PostgreSQL and a mounted volume.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ACA_", env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        extra="ignore", case_sensitive=False,
    )

    # --- app -------------------------------------------------------------
    app_name: str = "Autonomous Creator Agents"
    tagline: str = "Your AI-powered creative production team."
    environment: str = "development"          # development | production
    debug: bool = True
    api_prefix: str = "/api"

    # --- security --------------------------------------------------------
    # Generated per-install when unset (dev only). Production must set this.
    secret_key: str = Field(default="", description="signing key for session cookies")
    session_cookie: str = "aca_session"
    session_ttl_hours: int = 24 * 7
    cookie_secure: bool = False               # set true behind HTTPS
    cookie_samesite: str = "lax"
    password_iterations: int = 240_000
    max_login_attempts: int = 8
    login_window_seconds: int = 300

    # --- database --------------------------------------------------------
    # sqlite for local dev; e.g. postgresql+psycopg://user:pass@host:5432/aca in prod
    database_url: str = ""
    sql_echo: bool = False

    # --- storage ---------------------------------------------------------
    storage_root: str = ""
    max_upload_mb: int = 500
    allowed_video_ext: str = ".mp4,.mov,.m4v,.webm,.mkv"
    allowed_image_ext: str = ".jpg,.jpeg,.png,.webp"

    # --- processing ------------------------------------------------------
    clip_min_seconds: float = 3.0
    clip_max_seconds: float = 90.0
    max_segments: int = 8
    enable_whisper: bool = False
    whisper_model: str = "base"
    job_poll_seconds: float = 1.5

    # --- optional external AI -------------------------------------------
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # --- web -------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("environment")
    @classmethod
    def _known_env(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"development", "production", "test"}:
            raise ValueError("environment must be development, production or test")
        return v

    # --- derived paths ---------------------------------------------------
    @property
    def storage(self) -> Path:
        p = Path(self.storage_root) if self.storage_root else REPO_ROOT / "storage"
        return p.resolve()

    @property
    def uploads_dir(self) -> Path:
        return self.storage / "uploads"

    @property
    def clips_dir(self) -> Path:
        return self.storage / "clips"

    @property
    def thumbs_dir(self) -> Path:
        return self.storage / "thumbnails"

    @property
    def temp_dir(self) -> Path:
        return self.storage / "temp"

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.storage / 'aca.db').as_posix()}"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def video_exts(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_video_ext.split(",") if e.strip()}

    @property
    def image_exts(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_image_ext.split(",") if e.strip()}

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())

    def ensure_dirs(self) -> None:
        for d in (self.storage, self.uploads_dir, self.clips_dir, self.thumbs_dir, self.temp_dir):
            d.mkdir(parents=True, exist_ok=True)

    def resolved_secret(self) -> str:
        """Session signing key. Falls back to a per-install random value in dev."""
        if self.secret_key:
            return self.secret_key
        keyfile = self.storage / ".secret_key"
        if keyfile.exists():
            return keyfile.read_text(encoding="utf-8").strip()
        import secrets
        key = secrets.token_urlsafe(48)
        self.storage.mkdir(parents=True, exist_ok=True)
        keyfile.write_text(key, encoding="utf-8")
        try:
            keyfile.chmod(0o600)
        except OSError:
            pass
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


settings = get_settings()

# Names the video services import directly.
WORK_DIR = settings.temp_dir

# ---------------------------------------------------------------------------
# Delivery presets (resolution, crop strategy, caption limits per platform)
# ---------------------------------------------------------------------------
PLATFORM_PRESETS: dict[str, dict] = {
    "youtube_shorts": {"label": "YouTube Shorts", "width": 1080, "height": 1920,
                       "caption_chars": 32, "caption_lines": 2, "crop": "center",
                       "thumb_strategy": "blur_pad", "max_seconds": 60},
    "instagram_reel": {"label": "Instagram Reels", "width": 1080, "height": 1920,
                       "caption_chars": 30, "caption_lines": 2, "crop": "center",
                       "thumb_strategy": "blur_pad", "max_seconds": 90},
    "tiktok": {"label": "TikTok", "width": 1080, "height": 1920,
               "caption_chars": 28, "caption_lines": 2, "crop": "center",
               "thumb_strategy": "blur_pad", "max_seconds": 60},
    "youtube": {"label": "YouTube (16:9)", "width": 1920, "height": 1080,
                "caption_chars": 42, "caption_lines": 2, "crop": "fit",
                "thumb_strategy": "cover", "max_seconds": None},
    "square": {"label": "Square (1:1)", "width": 1080, "height": 1080,
               "caption_chars": 38, "caption_lines": 2, "crop": "blur_pad",
               "thumb_strategy": "cover", "max_seconds": 180},
}


# ---------------------------------------------------------------------------
# ffmpeg resolution: system binary first, then the static wheel
# ---------------------------------------------------------------------------
def ffmpeg_bin() -> str:
    env = os.getenv("FFMPEG_BIN")
    if env and Path(env).exists():
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "No ffmpeg found. Install ffmpeg, or `pip install imageio-ffmpeg`."
        ) from exc


@lru_cache(maxsize=8)
def ffmpeg_has(filter_name: str) -> bool:
    try:
        out = subprocess.run([ffmpeg_bin(), "-hide_banner", "-filters"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return False
    return any(line.split()[1:2] == [filter_name] for line in out.splitlines() if line.strip())
