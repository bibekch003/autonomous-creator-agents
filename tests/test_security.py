"""Security tests: upload validation, resource isolation, path traversal, injection."""
from __future__ import annotations

import uuid


def test_rejects_disallowed_upload_types(project):
    client, proj = project
    for name, payload in (("evil.exe", b"MZ\x90"), ("notes.txt", b"hello"),
                          ("clip.php", b"<?php echo 1; ?>")):
        r = client.post(f"/api/projects/{proj['id']}/videos",
                        files={"file": (name, payload, "application/octet-stream")})
        assert r.status_code == 422, f"{name} should be rejected"


def test_rejects_a_file_that_is_not_really_video(project):
    client, proj = project
    r = client.post(f"/api/projects/{proj['id']}/videos",
                    files={"file": ("fake.mp4", b"not a video at all", "video/mp4")})
    assert r.status_code == 422
    assert "Could not read this file as video" in r.json()["detail"]


def test_upload_size_limit_is_enforced(project, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "max_upload_mb", 0)   # any non-empty file is too big
    client, proj = project
    r = client.post(f"/api/projects/{proj['id']}/videos",
                    files={"file": ("big.mp4", b"x" * 2048, "video/mp4")})
    assert r.status_code in (413, 422)


def test_another_user_cannot_reach_private_resources(uploaded_video):
    client, _proj, video = uploaded_video
    project_id = video["project_id"]

    # Analyse with the owner so there is a clip and a thumbnail to try to reach.
    client.post(f"/api/videos/{video['id']}/analyse", params={"sync": True, "clip_seconds": 4})
    clip_id = client.post("/api/clips", params={"sync": True}, json={
        "video_id": video["id"], "start_s": 0, "end_s": 4}).json()["output"]["clips"][0]["clip_id"]
    thumb_id = client.post("/api/thumbnails/render", json={
        "video_id": video["id"], "clip_id": clip_id, "headline": "x"}).json()[0]["id"]

    # A second account, in a separate cookie jar.
    other = type(client)(client.app)
    with other as intruder:
        r = intruder.post("/api/auth/register", json={
            "name": "Intruder", "email": f"x-{uuid.uuid4().hex[:8]}@example.com",
            "password": "secret123"})
        assert r.status_code == 201

        for path in (f"/api/projects/{project_id}",
                     f"/api/videos/{video['id']}",
                     f"/api/videos/{video['id']}/stream",
                     f"/api/videos/{video['id']}/clips",
                     f"/api/clips/{clip_id}",
                     f"/api/clips/{clip_id}/download",
                     f"/api/thumbnails/{thumb_id}/image"):
            assert intruder.get(path).status_code == 404, path

        # ...and cannot delete it either
        assert intruder.delete(f"/api/clips/{clip_id}").status_code == 404
        assert intruder.delete(f"/api/projects/{project_id}").status_code == 404


def test_stored_filenames_are_server_generated(project, sample_video):
    """A hostile original name must not become a path on disk."""
    client, proj = project
    with sample_video.open("rb") as fh:
        r = client.post(f"/api/projects/{proj['id']}/videos",
                        files={"file": ("../../../etc/passwd.mp4", fh, "video/mp4")})
    assert r.status_code == 201
    body = r.json()
    assert "passwd" not in body["stream_url"]
    assert "/" not in body["original_name"]
    assert ".." not in body["original_name"]


def test_path_guard_blocks_traversal():
    from app.core.config import settings
    from app.services.storage import resolve_within
    assert resolve_within(settings.uploads_dir, "ok.mp4").name == "ok.mp4"
    for bad in ("../../etc/passwd", "/etc/passwd", "..", "a/../../b"):
        try:
            resolve_within(settings.uploads_dir, bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should have been refused")


def test_sql_injection_in_a_field_is_stored_as_text(project):
    client, proj = project
    payload = "Robert'); DROP TABLE projects;--"
    r = client.patch(f"/api/projects/{proj['id']}", json={"name": payload, "description": ""})
    assert r.status_code == 200 and r.json()["name"] == payload
    # the table still exists and the row is intact
    assert client.get("/api/projects").status_code == 200


def test_unknown_resources_return_404_not_500(project):
    client, _proj = project
    assert client.get("/api/projects/doesnotexist").status_code == 404
    assert client.get("/api/videos/doesnotexist").status_code == 404
    assert client.get("/api/clips/doesnotexist").status_code == 404
