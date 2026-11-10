"""Editing Agent — cut segments into platform-sized clips and burn subtitles."""
from __future__ import annotations

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent, AgentError
from app.core.config import PLATFORM_PRESETS, settings
from app.models import Clip, Transcript
from app.services import clips as clip_service


class EditingAgent(BaseAgent):
    name = "editing"
    title = "Editing"
    description = ("Renders selected moments to MP4 with FFmpeg: vertical 9:16, square 1:1 or "
                   "landscape 16:9, loudness-normalised, with platform-legal subtitles burned in "
                   "when a transcript exists.")
    capabilities = ["trim", "aspect conversion", "subtitle burn-in", "loudness normalisation"]

    def run(self, ctx: AgentContext) -> dict:
        video = ctx.video()
        source = settings.uploads_dir / video.stored_name
        if not source.exists():
            raise AgentError("The source video is missing from storage.")
        if not video.duration_s:
            raise AgentError("Run the Video Intelligence agent first: duration is unknown.")

        transcript = ctx.db.scalar(select(Transcript).where(Transcript.video_id == video.id))
        text = transcript.text if transcript else ""

        platform = ctx.params.get("platform") or "youtube_shorts"
        if platform not in PLATFORM_PRESETS:
            raise AgentError(f"Unknown platform '{platform}'.")
        burn = bool(ctx.params.get("burn_captions", True))

        # Either render explicit timestamps, or the suggested moments.
        wanted = ctx.params.get("clips")
        if not wanted:
            moments = (video.moments or [])[: int(ctx.params.get("count") or 3)]
            if not moments:
                raise AgentError("No moments to render. Run Video Intelligence first.")
            wanted = [{"start": m["start"], "end": m["end"], "reason": m.get("reason", ""),
                       "score": m.get("score", 0)} for m in moments]

        made: list[dict] = []
        for i, item in enumerate(wanted):
            start = float(item["start"])
            end = float(item["end"])
            if end <= start:
                ctx.log(f"Skipping invalid range {start}-{end}", "warning")
                continue
            # Re-rendering an existing clip (timestamps adjusted) reuses its row.
            clip = ctx.db.get(Clip, item["clip_id"]) if item.get("clip_id") else None
            if clip is not None and clip.user_id != video.user_id:
                raise AgentError("That clip belongs to another account.")
            if clip is None:
                clip = Clip(video_id=video.id, project_id=video.project_id,
                            user_id=video.user_id)
                ctx.db.add(clip)
            clip.title = item.get("title") or clip.title or f"Clip {i + 1}"
            clip.start_s = round(start, 2)
            clip.end_s = round(end, 2)
            clip.platform = platform
            clip.aspect = clip_service.aspect_for(platform)
            clip.status = "rendering"
            clip.reason = item.get("reason", clip.reason or "")
            clip.score = float(item.get("score") or clip.score or 0.0)
            ctx.db.commit()

            out_name = f"{clip.id}_{platform}.mp4"
            try:
                result = clip_service.render_clip(
                    video_path=source, out_dir=settings.clips_dir, out_name=out_name,
                    start=start, end=end, platform=platform, transcript_text=text,
                    video_duration=video.duration_s, burn_captions=burn,
                )
                clip.status = "ready"
                clip.output_name = result["output_name"]
                clip.file_size = int(result.get("size_mb", 0) * 1048576)
                clip.has_subtitles = bool(result.get("captions_burned"))
                clip.subtitle_name = result.get("subtitle_name", "")
                clip.error = ""
                ctx.log(f"Rendered {clip.title} ({start:.1f}s-{end:.1f}s) "
                        f"{clip.file_size / 1048576:.2f} MB"
                        f"{', captions burned' if clip.has_subtitles else ''}")
            except Exception as exc:
                clip.status = "failed"
                clip.error = str(exc)[:900]
                ctx.log(f"Render failed for {clip.title}: {exc}", "error")
            ctx.db.commit()
            ctx.progress(int(10 + 85 * (i + 1) / max(1, len(wanted))))
            made.append({"clip_id": clip.id, "status": clip.status,
                         "start": clip.start_s, "end": clip.end_s, "error": clip.error})

        ok = [m for m in made if m["status"] == "ready"]
        if not ok and made:
            raise AgentError("Every clip failed to render. Check the server logs.")
        return {"rendered": len(ok), "attempted": len(made), "platform": platform,
                "clips": made, "subtitles_available": bool(text)}
