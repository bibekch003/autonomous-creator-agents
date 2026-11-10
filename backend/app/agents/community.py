"""Community Agent — draft replies in the creator's voice, for human approval.

This agent deliberately cannot send anything. It produces a draft and stops, because
responding publicly on someone's behalf without review is the one mistake that cannot
be undone. The task lands in `awaiting_approval` and the UI shows it for a human.
"""
from __future__ import annotations

from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent, AgentError
from app.models import UserSettings
from app.services import seo as seo_service


class CommunityAgent(BaseAgent):
    name = "community"
    title = "Community"
    description = ("Drafts replies to comments in the creator's configured voice. Drafts are "
                   "returned for human approval and are never posted automatically.")
    capabilities = ["reply drafts", "persona consistency"]
    requires_approval = True

    def run(self, ctx: AgentContext) -> dict:
        comment = (ctx.params.get("comment") or "").strip()
        if not comment:
            raise AgentError("Provide the comment text to draft a reply for.")

        settings_row = ctx.db.scalar(
            select(UserSettings).where(UserSettings.user_id == ctx.user_id))
        persona = (ctx.params.get("persona") or
                   (settings_row.creator_persona if settings_row else "") or
                   "Direct, friendly, no hype.")
        topic = ctx.params.get("topic") or seo_service.topic_from(comment, "this video")

        ctx.log(f"Drafting a reply in persona: {persona[:80]}")
        draft = (
            f"Thanks for watching — genuinely useful question. "
            f"On {topic}: the short answer is that I measure it rather than guess, and the "
            f"numbers are in the video. If it helps, tell me which part you want me to go "
            f"deeper on and I'll cover it next."
        )

        if ctx.params.get("llm", True):
            from app.ai import client as ai
            data = ai.complete_json(
                "Draft a reply to a YouTube comment. Return STRICT JSON with one key: "
                "reply (string, under 400 characters, no emojis, no promises).\n"
                f"Creator persona: {persona}\nComment: {comment}\nTopic: {topic}"
            )
            if data and str(data.get("reply", "")).strip():
                draft = str(data["reply"]).strip()[:600]
                ctx.log("Reply drafted by the configured LLM endpoint")

        ctx.log("Draft ready. Waiting for human approval before anything is posted.")
        return {
            "draft": draft,
            "persona": persona,
            "comment": comment,
            "awaiting_approval": True,
            "note": ("Nothing is published by this agent. Approve the draft to mark it ready, "
                     "then post it yourself."),
        }
