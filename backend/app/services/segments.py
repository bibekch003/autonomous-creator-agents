"""Interesting-moment detection.

The claim this makes is deliberately narrow and testable: these are the passages with
the highest *measured* audio energy relative to the rest of the take, which is where
emphasis, raised voices and speech density cluster. It is a signal, not a guarantee,
and the reason string says so.

Nothing here predicts virality.
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services.video import audio, media


def detect_moments(video_path: str | Path, *, duration: float,
                   target_seconds: float | None = None,
                   max_segments: int | None = None) -> tuple[list[dict], dict]:
    """Return (moments, analysis) where analysis holds the raw signal for the UI."""
    target = target_seconds or float(settings.clip_max_seconds)
    target = max(settings.clip_min_seconds, min(target, float(settings.clip_max_seconds)))
    limit = max_segments or settings.max_segments

    waveform, sr = media.extract_audio(video_path)
    timeline = audio.timeline(waveform, sr)
    windows = audio.hook_windows(waveform, sr, window_s=3.0, k=max(6, limit * 2))
    cuts = media.scene_cuts(video_path)

    mean_energy = sum(b["energy"] for b in timeline) / len(timeline) if timeline else 0.0
    moments: list[dict] = []

    for win in windows:
        if len(moments) >= limit:
            break
        peak = float(win.get("start", 0.0))
        length = min(target, max(settings.clip_min_seconds, duration - 0.5))
        start = max(0.0, min(peak - 1.0, duration - length))
        end = min(duration, start + length)
        if end - start < settings.clip_min_seconds:
            continue
        if any(abs(start - m["start"]) < length * 0.5 for m in moments):
            continue  # keep suggestions distinct instead of stacking on one peak

        energy = float(win.get("energy", 0.0))
        speech = float(win.get("speech", 0.0))
        # 0-100 from measured signals only: energy above the take's average, plus
        # speech-band density. No model, no invented confidence.
        lift = (energy / mean_energy) if mean_energy > 0 else 1.0
        score = round(min(100.0, 45.0 * min(lift, 2.0) + 35.0 * min(1.0, speech * 3) + 20.0 * energy), 1)

        reasons = []
        if lift >= 1.15:
            reasons.append(f"audio energy {lift:.1f}x the take's average")
        else:
            reasons.append("audio energy at or above the take's average")
        if speech >= 0.35:
            reasons.append("dense speech in the 300-3400 Hz band")
        if any(abs(peak - c) < 1.5 for c in cuts):
            reasons.append("sits on a visual cut")
        moments.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "score": score,
            "label": f"{int(start // 60):02d}:{int(start % 60):02d}",
            "reason": ("Suggested because " + ", ".join(reasons) +
                       ". Measured from the audio track; this is a signal, not a prediction "
                       "of how the clip will perform."),
        })

    analysis = {
        "energy_timeline": timeline,
        "hook_windows": windows,
        "scene_cuts": cuts,
        "mean_energy": round(mean_energy, 4),
        "duration": duration,
    }
    return moments, analysis
