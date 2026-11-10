"""Shared pytest fixtures.

The environment is configured *before* importing the app, because settings are read
once at import time. Each test session gets its own storage directory and SQLite file,
so a test run never touches your development data.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

_TMP = Path(tempfile.mkdtemp(prefix="aca_tests_"))
os.environ.update({
    "ACA_STORAGE_ROOT": str(_TMP / "storage"),
    "ACA_ENVIRONMENT": "test",
    "ACA_DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    "ACA_SECRET_KEY": "test-only-secret-key",
    "ACA_ENABLE_WHISPER": "false",
    "ACA_LLM_API_KEY": "",
    "ACA_MAX_UPLOAD_MB": "50",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import ffmpeg_bin  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def sample_video() -> Path:
    """A small real MP4 with audio, generated locally with ffmpeg."""
    out = _TMP / "sample.mp4"
    if out.exists():
        return out
    cmd = [
        ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=12:duration=10",
        "-f", "lavfi", "-i", "sine=frequency=220:duration=10",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        pytest.skip(f"could not build the sample video: {proc.stderr[-300:]}")
    return out


@pytest.fixture(scope="session")
def client():
    """TestClient used as a context manager so the app's lifespan runs (creates schema)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def user_client(client):
    """A client signed in as a brand-new user."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"name": "Test User", "email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return client, email


@pytest.fixture()
def project(user_client):
    client, _email = user_client
    r = client.post("/api/projects", json={"name": "Test project", "description": "fixture"})
    assert r.status_code == 201, r.text
    return client, r.json()


@pytest.fixture()
def uploaded_video(project, sample_video):
    client, proj = project
    with sample_video.open("rb") as fh:
        r = client.post(f"/api/projects/{proj['id']}/videos",
                        files={"file": ("sample.mp4", fh, "video/mp4")})
    assert r.status_code == 201, r.text
    return client, proj, r.json()
