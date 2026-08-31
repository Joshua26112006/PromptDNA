"""Experiment & model endpoints (versioned under ``/api/v1``).

Thin: parse, call the service, return a schema. Authorization (owner-only run /
score, visibility-based read) lives in ``app/services/experiment.py``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.experiment import (
    ExperimentListResponse,
    ExperimentRead,
    ExperimentRunRequest,
    ExperimentScoreRequest,
    ModelRead,
)
from app.services import experiment as service

router = APIRouter(tags=["experiments"])

DbDep = Annotated[Session, Depends(get_db)]
PromptId = Annotated[uuid.UUID, Path(description="Prompt UUID.")]
VersionId = Annotated[uuid.UUID, Path(description="Version UUID.")]
ExperimentId = Annotated[uuid.UUID, Path(description="Experiment UUID.")]


@router.get("/models", response_model=list[ModelRead], summary="List AI models")
def list_models(db: DbDep, current_user: CurrentUser) -> list[ModelRead]:
    """Every model record, each with `execution_configured` (whether a
    registered provider for its `provider` has credentials on this server).
    API keys are never exposed."""

    return service.list_models(db)


@router.post(
    "/prompts/{prompt_id}/versions/{version_id}/experiments",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run an experiment: execute this version against a model (owner only)",
)
def run_experiment(
    prompt_id: PromptId,
    version_id: VersionId,
    payload: ExperimentRunRequest,
    db: DbDep,
    current_user: CurrentUser,
) -> ExperimentRead:
    """Executes **this immutable version's content** against `model_id` and
    records the result. Only the prompt owner may run experiments — a public
    prompt does not grant execution (`403`). The response is the completed
    experiment with `status` `SUCCESS` or `FAILED` (a failed provider call is
    recorded as `FAILED`, never faked as success). `503` if the model has no
    configured execution provider (no experiment is created)."""

    return service.run_experiment(
        db, prompt_id, version_id, current_user=current_user, data=payload
    )


@router.get(
    "/prompts/{prompt_id}/experiments",
    response_model=ExperimentListResponse,
    summary="List experiments for all of a prompt's versions",
)
def list_prompt_experiments(
    prompt_id: PromptId, db: DbDep, current_user: CurrentUser
) -> ExperimentListResponse:
    return service.list_for_prompt(db, prompt_id, current_user=current_user)


@router.get(
    "/prompts/{prompt_id}/versions/{version_id}/experiments",
    response_model=ExperimentListResponse,
    summary="List experiments for one version",
)
def list_version_experiments(
    prompt_id: PromptId,
    version_id: VersionId,
    db: DbDep,
    current_user: CurrentUser,
) -> ExperimentListResponse:
    return service.list_for_version(
        db, prompt_id, version_id, current_user=current_user
    )


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentRead,
    summary="Get one experiment (authorized through its prompt)",
)
def get_experiment(
    experiment_id: ExperimentId, db: DbDep, current_user: CurrentUser
) -> ExperimentRead:
    """An experiment id cannot bypass prompt authorization — if the caller
    cannot view the owning prompt, this returns `404`."""

    return service.get_experiment(db, experiment_id, current_user=current_user)


@router.patch(
    "/experiments/{experiment_id}",
    response_model=ExperimentRead,
    summary="Set an experiment's score / notes (owner only)",
)
def update_experiment(
    experiment_id: ExperimentId,
    payload: ExperimentScoreRequest,
    db: DbDep,
    current_user: CurrentUser,
) -> ExperimentRead:
    """`score` must be 0–10 (also enforced by a DB CHECK). Only the prompt
    owner may score. This never modifies the version or the execution result."""

    return service.update_experiment(
        db, experiment_id, current_user=current_user, data=payload
    )
