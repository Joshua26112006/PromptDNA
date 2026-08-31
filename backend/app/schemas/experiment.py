"""Experiment / Model request and response schemas.

An experiment records the execution of a **specific immutable prompt version**
against a **specific model**, preserving the output and execution metadata for
later comparison. The client controls almost nothing — see
``docs/api.md``.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

_NOTES_MAX = 20_000
SCORE_MIN = 0
SCORE_MAX = 10


class ExperimentRunRequest(BaseModel):
    """Body for ``POST .../versions/{version_id}/experiments``.

    ``experiment_id`` / ``version_id`` / ``prompt_id`` / ``executed_at`` /
    ``output`` / ``response_time_ms`` / ``status`` / ``error_message`` are
    all backend-controlled and rejected here.
    """

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, protected_namespaces=()
    )

    model_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=_NOTES_MAX)


class ExperimentScoreRequest(BaseModel):
    """Body for ``PATCH /experiments/{id}`` — owner-only score / notes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    score: float | None = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    notes: str | None = Field(default=None, max_length=_NOTES_MAX)


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    experiment_id: uuid.UUID
    version_id: uuid.UUID
    prompt_id: uuid.UUID
    model_id: uuid.UUID
    model_name: str
    provider: str
    version_number: int
    executed_at: datetime.datetime
    response_time_ms: int | None
    score: Decimal | None
    output: str | None
    notes: str | None
    status: str
    error_message: str | None


class ExperimentListResponse(BaseModel):
    items: list[ExperimentRead]
    total: int


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    model_id: uuid.UUID
    name: str
    provider: str
    created_at: datetime.datetime
    #: True when a registered provider for `provider` is configured to execute.
    execution_configured: bool
