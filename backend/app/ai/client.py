"""Optional external LLM adapter.

The app is fully functional without this. When ACA_LLM_API_KEY is set, SEO copy is
written by a model; otherwise a deterministic template engine produces it. Either way
the response records which engine actually ran (`source`), so the UI never claims AI
work it did not do.
"""
from __future__ import annotations

import json

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def is_enabled() -> bool:
    return settings.llm_enabled


def complete_json(prompt: str, *, timeout: float = 30.0) -> dict | None:
    """Ask an OpenAI-compatible endpoint for a JSON object. Returns None on any problem."""
    if not settings.llm_enabled:
        return None
    try:
        import httpx

        resp = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": settings.llm_model,
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        log.warning("LLM call failed, falling back to the offline engine: %s", exc)
        return None
