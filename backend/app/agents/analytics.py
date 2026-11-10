"""Analytics Agent — summarise the account's own production statistics.

Read-only by design: it reports what this application recorded. It does not import
platform analytics and never presents local counts as engagement data.
"""
from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.services import analytics as analytics_service


class AnalyticsAgent(BaseAgent):
    name = "analytics"
    title = "Analytics"
    description = ("Summarises projects, videos, clips and agent activity from this "
                   "application's own database. Locally generated statistics only — no "
                   "platform analytics are imported.")
    capabilities = ["production stats", "agent success rate", "storage usage"]

    def run(self, ctx: AgentContext) -> dict:
        data = analytics_service.detail(ctx.db, ctx.user_id)
        ctx.log(f"{data['videos_processed']}/{data['videos']} videos processed, "
                f"{data['clips_ready']}/{data['clips']} clips ready")
        total_tasks = data["tasks_succeeded"] + data["tasks_failed"]
        rate = (data["tasks_succeeded"] / total_tasks * 100) if total_tasks else 0.0
        return {
            "overview": data,
            "agent_success_rate": round(rate, 1),
            "source_note": data["source_note"],
        }
