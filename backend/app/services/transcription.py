"""Speech transcription with an honest adapter chain.

Order of preference:
1. `faster-whisper` — local ASR, only when ACA_ENABLE_WHISPER=true and installed.
2. A sidecar `.txt`/`.srt`/`.vtt` next to the uploaded file.
3. A transcript the user pasted in the UI.
4. Nothing.

If nothing is available the app says so (`source="none"`) and keeps working: moment
detection is audio-based, clips still render, and the SEO agent writes from the title
instead of inventing dialogue. It never fabricates a transcript.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.services.video.captions import Cue, build_cues, words_per_second

log = get_logger(__name__)

_SRT_NOISE = re.compile(r"^\s*(\d+|WEBVTT.*|\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->.*)\s*$")


def _from_sidecar(video_path: Path) -> tuple[str, list[Cue]] | None:
    for ext in (".txt", ".srt", ".vtt"):
        candidate = video_path.with_suffix(ext)
        if not candidate.exists():
            continue
        raw = candidate.read_text(encoding="utf-8", errors="ignore")
        if ext in {".srt", ".vtt"}:
            lines = [ln for ln in raw.splitlines() if not _SRT_NOISE.match(ln)]
            raw = " ".join(lines)
        text = re.sub(r"\s+", " ", raw).strip()
        if text:
            return text, []
    return None


def _from_whisper(video_path: Path) -> tuple[str, list[Cue]] | None:
    if not settings.enable_whisper:
        return None
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(str(video_path), vad_filter=True)
        cues: list[Cue] = []
        parts: list[str] = []
        for seg in segments:
            txt = seg.text.strip()
            if not txt:
                continue
            parts.append(txt)
            cues.append(Cue(float(seg.start), float(seg.end), txt))
        if parts:
            return " ".join(parts), cues
    except Exception as exc:  # not installed, model missing, corrupt audio
        log.warning("whisper transcription unavailable: %s", exc)
    return None


def transcribe(video_path: str | Path, *, stored_transcript: str | None = None,
               duration: float = 0.0) -> dict:
    """Return {text, cues, source}. `source` is one of whisper|sidecar|manual|none."""
    path = Path(video_path)

    if stored_transcript and stored_transcript.strip():
        return {"text": stored_transcript.strip(), "cues": [], "source": "manual"}

    got = _from_whisper(path)
    if got:
        text, cues = got
        return {"text": text, "cues": [_cue_dict(c) for c in cues], "source": "whisper"}

    got = _from_sidecar(path)
    if got:
        text, _ = got
        return {"text": text, "cues": [], "source": "sidecar"}

    return {"text": "", "cues": [], "source": "none"}


def _cue_dict(c: Cue) -> dict:
    return {"start": c.start, "end": c.end, "text": c.text}


def cues_for_window(text: str, start: float, end: float, *, video_duration: float,
                    max_chars: int = 32, max_lines: int = 2) -> list[Cue]:
    """Caption cues clipped to a clip window, sized for the platform."""
    if not text:
        return []
    return build_cues(text, start, max(0.5, end - start),
                      max_chars=max_chars, max_lines=max_lines,
                      video_duration=video_duration or None)


def transcript_quality(text: str, duration: float) -> dict:
    if not text:
        return {"available": False, "words": 0, "words_per_second": 0.0}
    words = len(text.split())
    return {
        "available": True,
        "words": words,
        "words_per_second": round(words / duration, 2) if duration else 0.0,
        "readable_pace": 1.2 <= (words / duration if duration else 0) <= 6.0,
    }


def cue_stats(cues: list[Cue]) -> dict:
    return {"count": len(cues), "words_per_second": words_per_second(cues) if cues else 0.0}
