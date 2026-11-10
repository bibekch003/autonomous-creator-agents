"""Design Agent — render and score thumbnail concepts for a clip or video."""
from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent, AgentError
from app.core.config import settings
from app.models import Thumbnail
from app.services import thumbnail_service


class DesignAgent(BaseAgent):
    name = "design"
    title = "Design"
    description = ("Renders thumbnail concepts from a real frame of the video and scores each "
                   "one on five measured sub-scores: contrast, colourfulness, subject presence, "
                   "text legibility and clutter.")
    capabilities = ["thumbnail rendering", "text layout", "visual scoring"]

    def run(self, ctx: AgentContext) -> dict:
        clip = None
        if ctx.params.get("clip_id") or ctx.task.clip_id:
            clip = ctx.clip()
            video = ctx.video(clip.video_id)
            at = clip.start_s + min(1.0, clip.duration_s / 3)
            headline = ctx.params.get("headline") or clip.title
            platform = clip.platform
        else:
            video = ctx.video()
            at = float(ctx.params.get("at_seconds") or 0.5)
            headline = ctx.params.get("headline") or video.original_name.rsplit(".", 1)[0]
            platform = ctx.params.get("platform") or "youtube_shorts"

        source = settings.uploads_dir / video.stored_name
        if not source.exists():
            raise AgentError("The source video is missing from storage.")

        styles = ctx.params.get("styles") or thumbnail_service.DEFAULT_STYLES
        ctx.log(f"Rendering {len(styles)} thumbnail concept(s) at {at:.1f}s "
                f"for platform '{platform}'")
        ctx.progress(30)

        rendered = thumbnail_service.render_set(
            video_path=source, at_seconds=at, headline=headline,
            out_dir=settings.thumbs_dir, platform=platform, styles=styles,
            name_prefix=f"{clip.id if clip else video.id}",
        )

        saved: list[dict] = []
        for item in rendered:
            row = Thumbnail(
                clip_id=clip.id if clip else None, video_id=video.id, user_id=video.user_id,
                headline=item["headline"], style=item["style"],
                width=item["width"], height=item["height"],
                stored_name=item["stored_name"], score=item["score"],
            )
            ctx.db.add(row)
            ctx.db.commit()
            ctx.log(f"{item['style']}: score {item['score']['score']}/100 "
                    f"({'; '.join(item['score'].get('reasons', [])[:2])})")
            saved.append({"thumbnail_id": row.id, "style": row.style,
                          "score": item["score"]["score"],
                          "reasons": item["score"].get("reasons", [])})

        ctx.progress(100)
        best = max(saved, key=lambda s: s["score"]) if saved else None
        return {"thumbnails": saved, "best": best, "count": len(saved)}
