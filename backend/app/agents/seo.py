"""SEO Agent — titles, descriptions, hashtags and platform-specific copy."""
from __future__ import annotations

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent
from app.models import GeneratedContent, Transcript
from app.services import seo as seo_service


class SEOAgent(BaseAgent):
    name = "seo"
    title = "SEO"
    description = ("Writes three title options, a description, hashtags, a short caption and "
                   "platform-specific variants. Uses the configured LLM when available, "
                   "otherwise a deterministic template engine.")
    capabilities = ["titles", "descriptions", "hashtags", "captions", "platform variants"]

    def run(self, ctx: AgentContext) -> dict:
        clip = None
        if ctx.params.get("clip_id") or ctx.task.clip_id:
            clip = ctx.clip()
            video = ctx.video(clip.video_id)
            platform = clip.platform
            base_title = clip.title
        else:
            video = ctx.video()
            platform = ctx.params.get("platform") or "youtube_shorts"
            base_title = video.original_name.rsplit(".", 1)[0]

        transcript = ctx.db.scalar(select(Transcript).where(Transcript.video_id == video.id))
        text = transcript.text if transcript else ""
        topic = ctx.params.get("topic") or seo_service.topic_from(text, base_title)

        ctx.log(f"Writing copy for '{topic}' on {platform}"
                f" (transcript: {'yes' if text else 'no'})")
        result = seo_service.generate(
            topic=topic, transcript=text, platform=platform,
            persona=ctx.params.get("persona", ""), clip_title=base_title,
        )

        # Replace previous generated copy for this clip so reruns do not pile up.
        if clip:
            for old in ctx.db.scalars(
                    select(GeneratedContent).where(GeneratedContent.clip_id == clip.id)).all():
                ctx.db.delete(old)
            ctx.db.commit()

        rows: list[dict] = []
        def add(kind: str, body: str, plat: str = "") -> None:
            row = GeneratedContent(project_id=video.project_id,
                                   clip_id=clip.id if clip else None,
                                   kind=kind, platform=plat, body=body,
                                   source=result["source"])
            ctx.db.add(row)
            rows.append({"kind": kind, "platform": plat, "body": body})

        for i, title in enumerate(result["titles"]):
            add("title", title)
        add("description", result["description"])
        add("hashtags", " ".join(result["hashtags"]))
        add("caption", result["caption"])
        for plat, body in result["platform_text"].items():
            add("platform_text", body, plat)
        ctx.db.commit()

        ctx.log(f"Saved {len(rows)} content items via the {result['source']} engine")
        return {
            "source": result["source"],
            "note": result["note"],
            "topic": topic,
            "titles": result["titles"],
            "description": result["description"],
            "hashtags": result["hashtags"],
            "caption": result["caption"],
            "items": len(rows),
        }
