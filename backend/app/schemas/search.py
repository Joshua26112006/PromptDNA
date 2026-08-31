"""Semantic-search / embedding schemas.

The raw embedding vector is never in a response. ``similarity`` is a
**semantic-similarity** score (how close two texts' meanings are) — distinct
from an experiment ``score`` (how well a model run performed).
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SemanticSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prompt_id: uuid.UUID
    version_id: uuid.UUID
    prompt_title: str
    version_number: int
    content_preview: str
    #: 1 - cosine_distance; higher = more semantically similar.
    similarity: float
    is_public: bool
    created_at: datetime.datetime


class SemanticSearchResponse(BaseModel):
    query: str
    count: int
    results: list[SemanticSearchResult]


class VersionEmbeddingStatus(BaseModel):
    version_id: uuid.UUID
    has_embedding: bool
    embedding_model: str | None
    dimension: int


class SemanticSearchParams(BaseModel):
    """Not a request body — documents the query params for `GET /search/semantic`."""

    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
