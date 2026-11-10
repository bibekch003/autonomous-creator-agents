"""Unit tests for the pieces that do not need HTTP: crypto, storage, SEO, moments."""
from __future__ import annotations

import pytest


# --- password hashing ------------------------------------------------------
def test_password_hash_round_trip():
    from app.core.security import hash_password, verify_password
    stored = hash_password("correct horse battery", iterations=1000)
    assert stored.startswith("pbkdf2_sha256$")
    assert "correct horse battery" not in stored
    assert verify_password("correct horse battery", stored) is True
    assert verify_password("wrong password", stored) is False


def test_same_password_hashes_differently():
    from app.core.security import hash_password
    a = hash_password("same-password-123", iterations=1000)
    b = hash_password("same-password-123", iterations=1000)
    assert a != b, "a random salt per hash is required"


def test_short_passwords_are_refused():
    from app.core.security import hash_password
    with pytest.raises(ValueError):
        hash_password("short")


def test_verify_survives_a_malformed_hash():
    from app.core.security import verify_password
    assert verify_password("anything", "not-a-hash") is False
    assert verify_password("anything", "") is False


# --- rate limiting ---------------------------------------------------------
def test_rate_limiter_blocks_after_the_limit():
    from app.core.security import rate_limit_hit, rate_limit_reset
    key = "test-key"
    rate_limit_reset(key)
    results = [rate_limit_hit(key, limit=3, window=60) for _ in range(5)]
    assert results[:3] == [False, False, False]
    assert results[3] is True and results[4] is True
    rate_limit_reset(key)


# --- storage helpers -------------------------------------------------------
def test_filename_cleaning_strips_paths():
    from app.services.storage import clean_filename
    assert clean_filename("../../etc/passwd") == "passwd"
    assert "/" not in clean_filename("a/b/c.mp4")
    assert clean_filename("") == "file"


def test_upload_validation_rules():
    from app.core.config import settings
    from app.services.storage import validate_video_upload
    assert validate_video_upload("clip.MP4", 1024) == ".mp4"
    for bad in ("clip.exe", "clip", "clip.txt"):
        with pytest.raises(ValueError):
            validate_video_upload(bad, 1024)
    with pytest.raises(ValueError):
        validate_video_upload("clip.mp4", 0)
    with pytest.raises(ValueError):
        validate_video_upload("clip.mp4", (settings.max_upload_mb + 1) * 1024 * 1024)


def test_stored_names_are_unique_and_random():
    from app.services.storage import new_stored_name
    names = {new_stored_name(".mp4") for _ in range(50)}
    assert len(names) == 50
    assert all(n.endswith(".mp4") for n in names)


# --- SEO engine ------------------------------------------------------------
def test_seo_offline_engine_shape():
    from app.services.seo import generate
    out = generate(topic="hook retention", transcript="", platform="youtube_shorts")
    assert out["source"] == "offline"
    assert len(out["titles"]) == 3 and all(t.strip() for t in out["titles"])
    assert out["description"] and out["caption"]
    assert all(h.startswith("#") for h in out["hashtags"])
    assert set(out["platform_text"]) >= {"youtube_shorts", "tiktok", "youtube"}


def test_seo_topic_extraction_skips_stopwords():
    from app.services.seo import topic_from
    topic = topic_from("I spent three years editing my own videos", "fallback")
    assert topic and topic not in {"the", "and", "own"}


# --- moment detection maths ------------------------------------------------
def test_moments_are_ordered_and_non_overlapping(sample_video):
    from app.services.segments import detect_moments
    moments, analysis = detect_moments(sample_video, duration=10.0, target_seconds=4)
    assert moments, "expected suggestions for a real audio track"
    for m in moments:
        assert m["end"] > m["start"]
        assert 0 <= m["score"] <= 100
        assert "signal, not a prediction" in m["reason"]
    # Ranked by measured score (best first), so assert distinctness instead of order.
    for i, a in enumerate(moments):
        for b in moments[i + 1:]:
            assert abs(a["start"] - b["start"]) > 0.5, "suggestions must be distinct moments"
        assert a["end"] <= 10.5
    assert analysis["energy_timeline"], "the audio analysis must be returned for the UI"


def test_moments_respect_the_requested_length(sample_video):
    from app.services.segments import detect_moments
    moments, _ = detect_moments(sample_video, duration=10.0, target_seconds=5, max_segments=2)
    assert len(moments) <= 2
    for m in moments:
        assert m["end"] - m["start"] <= 5.5


# --- transcription honesty -------------------------------------------------
def test_transcription_never_invents_text(tmp_path):
    from app.services.transcription import transcribe
    fake = tmp_path / "video.mp4"
    fake.write_bytes(b"\x00" * 1024)
    result = transcribe(fake)
    assert result["source"] == "none" and result["text"] == ""


def test_sidecar_transcript_is_used(tmp_path):
    from app.services.transcription import transcribe
    fake = tmp_path / "video.mp4"
    fake.write_bytes(b"\x00" * 1024)
    (tmp_path / "video.txt").write_text("This is my real script.", encoding="utf-8")
    result = transcribe(fake)
    assert result["source"] == "sidecar"
    assert result["text"] == "This is my real script."


# --- thumbnails ------------------------------------------------------------
def test_thumbnail_scoring_reports_reasons(sample_video):
    from app.core.config import settings
    from app.services.thumbnail_service import render_set
    out = render_set(video_path=sample_video, at_seconds=1.0, headline="Test headline",
                     out_dir=settings.thumbs_dir, platform="youtube_shorts",
                     styles=["bold_lower"])
    assert len(out) == 1
    score = out[0]["score"]
    assert 0 <= score["score"] <= 100
    assert score["reasons"], "a score without reasons is not explainable"
    assert (settings.thumbs_dir / out[0]["stored_name"]).exists()
