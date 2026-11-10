"""Clip rendering: cut a segment, size it for a platform, burn captions if asked."""
from __future__ import annotations

from pathlib import Path

from app.core.config import PLATFORM_PRESETS, WORK_DIR
from app.core.logging import get_logger
from app.services.transcription import cues_for_window
from app.services.video import captions as cap
from app.services.video import formats

log = get_logger(__name__)


def aspect_for(platform: str) -> str:
    preset = PLATFORM_PRESETS.get(platform, PLATFORM_PRESETS["youtube_shorts"])
    if preset["height"] > preset["width"]:
        return "vertical"
    if preset["height"] == preset["width"]:
        return "square"
    return "landscape"


def render_clip(*, video_path: Path, out_dir: Path, out_name: str, start: float, end: float,
                platform: str, transcript_text: str, video_duration: float,
                burn_captions: bool = True) -> dict:
    """Render one clip. Returns a result dict; raises on failure so the caller can retry."""
    preset = PLATFORM_PRESETS.get(platform)
    if preset is None:
        raise ValueError(f"Unknown platform '{platform}'")

    duration = max(0.5, end - start)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name

    cues = cues_for_window(
        transcript_text, start, end, video_duration=video_duration,
        max_chars=preset["caption_chars"], max_lines=preset["caption_lines"],
    )
    srt_path = WORK_DIR / f"{out_name}.srt"
    srt_path.write_text(cap.to_srt(cues), encoding="utf-8")
    vtt_path = WORK_DIR / f"{out_name}.vtt"
    vtt_path.write_text(cap.to_vtt(cues), encoding="utf-8")

    result = formats.export_clip(
        video_path, out_path, platform=platform, start=start, duration=duration,
        srt_path=srt_path, burn_captions=burn_captions and bool(cues), cues=cues,
    )
    result.update({
        "output_name": out_name,
        "subtitle_name": srt_path.name,
        "subtitle_path": str(srt_path),
        "vtt_path": str(vtt_path),
        "caption_count": len(cues),
        "captions_burned": bool(result.get("captions_burned")),
    })
    return result


def probe_output(path: Path) -> dict:
    """Metadata for a rendered clip, so the UI can show what was produced."""
    from app.services.video import media
    try:
        meta = media.probe(path)
        return {"duration_s": meta["duration"], "width": meta["width"],
                "height": meta["height"], "size_bytes": path.stat().st_size}
    except Exception:
        return {"size_bytes": path.stat().st_size if path.exists() else 0}
