"""Authentication, session and authorisation tests."""
from __future__ import annotations

import uuid


def _email() -> str:
    return f"auth-{uuid.uuid4().hex[:10]}@example.com"


def test_register_login_logout_cycle(client):
    email = _email()
    r = client.post("/api/auth/register",
                    json={"name": "Asha", "email": email, "password": "secret123"})
    assert r.status_code == 201
    assert r.json()["user"]["email"] == email
    assert "password" not in str(r.json()).lower()

    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    r = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_duplicate_email_is_rejected(client):
    email = _email()
    body = {"name": "Dup", "email": email, "password": "secret123"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409


def test_short_password_is_rejected(client):
    r = client.post("/api/auth/register",
                    json={"name": "Short", "email": _email(), "password": "abc"})
    assert r.status_code == 422


def test_wrong_password_and_unknown_email_look_identical(client):
    email = _email()
    client.post("/api/auth/register",
                json={"name": "Same", "email": email, "password": "secret123"})
    wrong = client.post("/api/auth/login", json={"email": email, "password": "nope1234"})
    unknown = client.post("/api/auth/login",
                          json={"email": f"nobody-{uuid.uuid4().hex[:6]}@example.com",
                                "password": "nope1234"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_protected_routes_require_a_session(client):
    client.cookies.clear()
    for path in ("/api/projects", "/api/agents", "/api/analytics/overview", "/api/settings"):
        assert client.get(path).status_code == 401, path


def test_session_cookie_is_httponly(client):
    r = client.post("/api/auth/register",
                    json={"name": "Cookie", "email": _email(), "password": "secret123"})
    cookie_header = r.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()
    assert "aca_session" in cookie_header
