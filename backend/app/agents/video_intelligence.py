"""Video Intelligence Agent — analyse a video, transcribe it, find interesting moments."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent, AgentError
from app.core.config import settings
from app.models import Transcript
from app.services import segments, transcription
from app.services.video import media


class VideoIntelligenceAgent(BaseAgent):
    name = "video_intelligence"
    title = "Video Intelligence"
    description = ("Probes the file, extracts the audio track, transcribes speech when an "
                   "ASR engine is available, and ranks the passages with the highest "
                   "measured audio energy as clip candidates.")
    capabilities = ["probe", "audio analysis", "transcription", "moment detection"]

    def run(self, ctx: AgentContext) -> dict:
        video = ctx.video()
        path = settings.uploads_dir / video.stored_name
        if not path.exists():
            raise AgentError("The uploaded file is missing from storage.")

        video.status = "analysing"
        ctx.db.commit()
        ctx.log(f"Analysing {video.original_name} ({video.size_bytes / 1048576:.1f} MB)")
        ctx.progress(10)

        meta = media.probe(path)
        video.duration_s = meta["duration"]
        video.width, video.height = meta["width"], meta["height"]
        video.fps = meta["fps"]
        video.has_audio = meta["has_audio"]
        ctx.db.commit()
        ctx.log(f"Probe: {meta['width']}x{meta['height']}, {meta['fps']} fps, "
                f"{meta['duration']}s, audio={'yes' if meta['has_audio'] else 'no'}")
        ctx.progress(25)

        # --- transcript (never invented) ---------------------------------
        existing = ctx.db.scalar(select(Transcript).where(Transcript.video_id == video.id))
        tr = transcription.transcribe(
            path,
            stored_transcript=(ctx.params.get("transcript") or
                               (existing.text if existing and existing.source == "manual" else None)),
            duration=video.duration_s,
        )
        if tr["text"]:
            if existing is None:
                existing = Transcript(video_id=video.id)
                ctx.db.add(existing)
            existing.text = tr["text"]
            existing.source = tr["source"]
            existing.cues = tr["cues"]
            ctx.db.commit()
            ctx.log(f"Transcript ready via {tr['source']} ({len(tr['text'].split())} words)")
        else:
            ctx.log("No transcript available: no ASR engine, no sidecar file and no pasted "
                    "text. Captions and transcript-based copy will be skipped.", "warning")
        ctx.progress(45)

        # --- moments ------------------------------------------------------
        target = float(ctx.params.get("clip_seconds") or settings.clip_max_seconds)
        moments, analysis = segments.detect_moments(
            path, duration=video.duration_s, target_seconds=target)
        video.moments = moments
        video.analysis = analysis
        video.status = "ready"
        video.error = ""
        ctx.db.commit()
        ctx.progress(100)

        ctx.log(f"Found {len(moments)} candidate moments; top score "
                f"{moments[0]['score'] if moments else 0}")
        return {
            "video_id": video.id,
            "duration_s": video.duration_s,
            "moments": moments,
            "transcript_source": tr["source"],
            "transcript_words": len(tr["text"].split()) if tr["text"] else 0,
            "scene_cuts": len(analysis.get("scene_cuts", [])),
        }
