"""Safe file handling: upload validation, atomic writes, path-traversal guards."""
from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def clean_filename(name: str) -> str:
    """Display-only sanitised name. Never used to build a filesystem path."""
    base = Path(name or "file").name
    return _UNSAFE.sub("_", base)[:200] or "file"


def validate_video_upload(filename: str, size_bytes: int) -> str:
    """Validate before writing anything. Returns the normalised extension."""
    ext = Path(filename or "").suffix.lower()
    if ext not in settings.video_exts:
        raise ValueError(
            f"Unsupported file type '{ext or 'none'}'. Allowed: "
            f"{', '.join(sorted(settings.video_exts))}"
        )
    if size_bytes <= 0:
        raise ValueError("The file is empty.")
    limit = settings.max_upload_mb * 1024 * 1024
    if size_bytes > limit:
        raise ValueError(
            f"File is {size_bytes / 1048576:.1f} MB; the limit is "
            f"{settings.max_upload_mb} MB."
        )
    return ext


def validate_image_upload(filename: str, size_bytes: int) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in settings.image_exts:
        raise ValueError(f"Unsupported image type. Allowed: {', '.join(sorted(settings.image_exts))}")
    if size_bytes > 20 * 1024 * 1024:
        raise ValueError("Image is larger than 20 MB.")
    return ext


def new_stored_name(ext: str) -> str:
    """Server-generated filename: never derived from user input."""
    return f"{uuid.uuid4().hex}{ext}"


def save_stream(src: BinaryIO, dest: Path, max_bytes: int) -> int:
    """Stream an upload to disk, enforcing the size limit as we go.

    Writing to a temp file and renaming means a failed or oversized upload never
    leaves a partial file that the app might later try to process.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    written = 0
    try:
        with tmp.open("wb") as out:
            while True:
                chunk = src.read(1024 * 256)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError(
                        f"Upload exceeded the {max_bytes // 1048576} MB limit."
                    )
                out.write(chunk)
        if written == 0:
            raise ValueError("The uploaded file was empty.")
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return written


def resolve_within(root: Path, *parts: str) -> Path:
    """Join under `root` and refuse anything that escapes it (path traversal)."""
    candidate = (root.joinpath(*parts)).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Invalid path.")
    return candidate


def safe_delete(path: Path) -> None:
    """Delete a file only if it lives inside the storage root."""
    try:
        resolved = path.resolve()
        root = settings.storage.resolve()
        if root in resolved.parents and resolved.is_file():
            resolved.unlink()
    except OSError:
        pass


def disk_usage_mb(path: Path | None = None) -> float:
    target = path or settings.storage
    total = 0
    if target.exists():
        for p in target.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    continue
    return round(total / 1048576, 2)


def delete_project_files(video_files: list[str], clip_files: list[str],
                         thumb_files: list[str]) -> None:
    for name in video_files:
        safe_delete(settings.uploads_dir / name)
    for name in clip_files:
        safe_delete(settings.clips_dir / name)
    for name in thumb_files:
        safe_delete(settings.thumbs_dir / name)


def copy_into_storage(src: Path, dest_dir: Path, name: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copyfile(src, dest)
    return dest
