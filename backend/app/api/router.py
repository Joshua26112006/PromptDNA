"""Aggregate router for the versioned API (``/api/v1``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, experiments, graph, prompts, search
from app.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(prompts.router)
api_router.include_router(experiments.router)
api_router.include_router(search.router)
api_router.include_router(graph.router)
