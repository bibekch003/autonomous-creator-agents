"""Thumbnail generation and scoring.

Rendering is Pillow; scoring is OpenCV across five named sub-scores. Every score ships
with human-readable reasons, so the UI can explain itself instead of showing a number.
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import PLATFORM_PRESETS
from app.services.video import media, thumbs

DEFAULT_STYLES = ["bold_lower", "split_band", "top_strip"]


def render_set(*, video_path: Path, at_seconds: float, headline: str,
               out_dir: Path, platform: str = "youtube_shorts",
               styles: list[str] | None = None, name_prefix: str = "thumb") -> list[dict]:
    """Render one thumbnail per style, score each, return metadata."""
    preset = PLATFORM_PRESETS.get(platform, PLATFORM_PRESETS["youtube_shorts"])
    width, height = preset["width"], preset["height"]
    strategy = preset.get("thumb_strategy", "cover")

    frame = media.extract_frame(video_path, max(0.0, at_seconds))
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for i, style in enumerate(styles or DEFAULT_STYLES):
        style = style if style in thumbs.STYLE_PRESETS else "bold_lower"
        name = f"{name_prefix}_{i}_{style}.jpg"
        path = out_dir / name
        rendered = thumbs.render_variant(
            frame, headline or "Your hook goes here", style, width, height, path,
            strategy=strategy,
        )
        score = thumbs.score_thumbnail(path, rendered["text_box"])
        results.append({
            "stored_name": name,
            "style": style,
            "width": width,
            "height": height,
            "headline": headline,
            "score": score,
            "text_box": rendered["text_box"],
        })
    return results


def validate_custom_image(path: Path) -> dict:
    """Basic sanity check for a user-uploaded thumbnail."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            w, h = img.size
            img.verify()
        ok = w >= 320 and h >= 320
        return {
            "ok": ok,
            "width": w,
            "height": h,
            "warning": "" if ok else "Smaller than 320px on a side; text may be unreadable.",
        }
    except Exception as exc:
        return {"ok": False, "width": 0, "height": 0, "warning": f"Not a readable image: {exc}"}
