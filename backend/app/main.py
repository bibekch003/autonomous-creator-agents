"""FastAPI application entry point.

Run locally:      uvicorn app.main:app --reload --port 8000
Worker (separate): python -m app.workers.worker
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.agents.orchestrator import list_agents
from app.api import api_router
from app.ai import client as ai_client
from app.core.config import PLATFORM_PRESETS, REPO_ROOT, ffmpeg_bin, ffmpeg_has, settings
from app.core.database import create_all
from app.core.logging import get_logger, setup_logging

log = get_logger(__name__)
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    settings.ensure_dirs()
    if settings.environment != "production":
        # Convenience for local dev; production schema is managed by Alembic.
        create_all()
    log.info("%s v%s starting (env=%s, db=%s)", settings.app_name, __version__,
             settings.environment, settings.db_url.split("://")[0])
    log.info("ffmpeg: %s | caption burn-in: %s | LLM: %s",
             ffmpeg_bin(), ffmpeg_has("subtitles"),
             "configured" if ai_client.is_enabled() else "offline engine")
    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.tagline,
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,          # session cookie must travel with requests
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "ffmpeg": ffmpeg_bin(),
        "caption_burn_in": ffmpeg_has("subtitles"),
        "llm_configured": ai_client.is_enabled(),
        "whisper_enabled": settings.enable_whisper,
        "max_upload_mb": settings.max_upload_mb,
    }


@app.get(f"{settings.api_prefix}/meta", tags=["meta"])
def meta() -> dict:
    """Everything the UI needs to render itself without hardcoding backend knowledge."""
    return {
        "app_name": settings.app_name,
        "tagline": settings.tagline,
        "version": __version__,
        "platforms": [{"key": k, "label": v["label"], "width": v["width"],
                       "height": v["height"]} for k, v in PLATFORM_PRESETS.items()],
        "agents": list_agents(),
        "limits": {
            "max_upload_mb": settings.max_upload_mb,
            "clip_min_seconds": settings.clip_min_seconds,
            "clip_max_seconds": settings.clip_max_seconds,
            "max_segments": settings.max_segments,
            "video_extensions": sorted(settings.video_exts),
        },
        "engines": {
            "llm": "configured" if ai_client.is_enabled() else "offline template engine",
            "asr": ("faster-whisper" if settings.enable_whisper else "sidecar/pasted text only"),
        },
    }


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    """Last resort: log the detail, return a clean message, never leak a traceback."""
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server."})


# ---------------------------------------------------------------------------
# Serve the built React app when it exists (single-container deploys).
# In development the Vite dev server proxies /api instead.
# ---------------------------------------------------------------------------
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "app": settings.app_name,
            "message": "API is running. Start the frontend with `npm run dev` in frontend/, "
                       "or build it (npm run build) to serve the UI from here.",
            "docs": "/api/docs",
        }
