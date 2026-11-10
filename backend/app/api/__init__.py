"""API package: one router per concern, mounted by main.py."""
from fastapi import APIRouter

from app.api import (routes_agents, routes_auth, routes_clips, routes_content,
                     routes_media, routes_misc, routes_projects, routes_thumbnails)

api_router = APIRouter()
for module in (routes_auth, routes_projects, routes_media, routes_clips,
               routes_content, routes_thumbnails, routes_agents, routes_misc):
    api_router.include_router(module.router)

__all__ = ["api_router"]
