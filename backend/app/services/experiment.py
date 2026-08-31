"""Experiment business logic: run a prompt version against a model, record it.

Concept
-------
An experiment records the execution of a **specific immutable prompt version**
against a **specific model** at a point in time, preserving the output and
execution metadata (status, response time, timestamp) for later comparison.
Reproducibility is why an experiment references ``version_id`` directly and runs
``version.content`` verbatim — never a prompt reconstructed from title/metadata.

Authorization
-------------
* **Run** and **score**: prompt **owner only**. A public prompt grants *read*
  of prompts/versions/experiments but never execution → non-owner gets ``403``
  (public) or ``404`` (private / missing).
* **Read** experiments: follows the parent prompt's visibility (owner or
  ``is_public``); otherwise ``404``.

Transaction strategy
--------------------
No database transaction is held open across the external provider call:

    validate  ->  BEGIN; INSERT experiment (PENDING); COMMIT
              ->  provider.generate(...)          [timed, timed-out]
              ->  BEGIN; UPDATE experiment (SUCCESS|FAILED, output/error,
                         response_time_ms, executed_at); COMMIT

Response time is the wall-clock duration of the provider call measured with
``time.perf_counter()`` (a monotonic timer), stored as integer milliseconds.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.api.errors import (
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.db.models import Experiment, Model, Prompt, User, Version
from app.providers.base import ProviderError
from app.providers.registry import get_provider
from app.repositories import experiment as repo
from app.repositories import model as model_repo
from app.repositories import prompt as prompt_repo
from app.schemas.experiment import (
    ExperimentListResponse,
    ExperimentRead,
    ExperimentRunRequest,
    ExperimentScoreRequest,
    ModelRead,
)
from app.core.config import get_settings

logger = logging.getLogger("promptdna")

STATUS_PENDING = "PENDING"
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
_ERROR_MAX = 500


# --------------------------------------------------------------------------- #
# Authorization helpers (operate on an already-loaded Prompt)                #
# --------------------------------------------------------------------------- #
def _assert_viewable(prompt: Prompt, user: User) -> None:
    if not (prompt.user_id == user.user_id or prompt.is_public):
        raise NotFoundError("Prompt not found.")


def _assert_owner(prompt: Prompt, user: User) -> None:
    if prompt.user_id == user.user_id:
        return
    if prompt.is_public:
        raise ForbiddenError("Only the prompt owner can run or score experiments.")
    raise NotFoundError("Prompt not found.")


# --------------------------------------------------------------------------- #
# Serialization                                                             #
# --------------------------------------------------------------------------- #
def _to_read(experiment: Experiment) -> ExperimentRead:
    return ExperimentRead(
        experiment_id=experiment.experiment_id,
        version_id=experiment.version_id,
        prompt_id=experiment.version.prompt_id,
        model_id=experiment.model_id,
        model_name=experiment.model.name,
        provider=experiment.model.provider,
        version_number=experiment.version.version_number,
        executed_at=experiment.executed_at,
        response_time_ms=experiment.response_time_ms,
        score=experiment.score,
        output=experiment.output,
        notes=experiment.notes,
        status=experiment.status,
        error_message=experiment.error_message,
    )


def _reload_read(db: Session, experiment_id: uuid.UUID) -> ExperimentRead:
    fresh = repo.get_experiment_by_id(db, experiment_id)
    assert fresh is not None
    return _to_read(fresh)


# --------------------------------------------------------------------------- #
# Run                                                                       #
# --------------------------------------------------------------------------- #
def run_experiment(
    db: Session,
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
    *,
    current_user: User,
    data: ExperimentRunRequest,
) -> ExperimentRead:
    settings = get_settings()

    # --- validate (no experiment row is created if any of these fail) -----
    prompt = prompt_repo.get_prompt_by_id(db, prompt_id)
    if prompt is None:
        raise NotFoundError("Prompt not found.")
    _assert_owner(prompt, current_user)

    version: Version | None = next(
        (v for v in prompt.versions if v.version_id == version_id), None
    )
    if version is None:
        raise NotFoundError("Version not found.")

    model: Model | None = model_repo.get_by_id(db, data.model_id)
    if model is None:
        raise NotFoundError("Model not found.")

    provider = get_provider(model.provider)
    if provider is None:
        raise ServiceUnavailableError(
            f"Model '{model.name}' has no registered execution provider."
        )
    if not provider.is_configured():
        raise ServiceUnavailableError(
            f"The execution provider for '{model.name}' is not configured on "
            f"this server."
        )

    prompt_text = version.content  # immutable version content, verbatim

    # --- transaction 1: PENDING -----------------------------------------
    experiment = repo.add_experiment(
        db,
        version_id=version.version_id,
        model_id=model.model_id,
        status=STATUS_PENDING,
        notes=data.notes,
    )
    experiment_id = experiment.experiment_id
    db.commit()

    # --- external call (no open transaction) --------------------------
    started = time.perf_counter()
    try:
        output = provider.generate(
            model_name=model.name,
            prompt_text=prompt_text,
            timeout_s=settings.experiment_provider_timeout_s,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        outcome = dict(status=STATUS_SUCCESS, output=output, error_message=None)
    except ProviderError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "experiment %s failed: %s", experiment_id, type(exc).__name__
        )
        outcome = dict(
            status=STATUS_FAILED,
            output=None,
            error_message=exc.safe_message[:_ERROR_MAX],
        )
    except Exception:  # pragma: no cover - defensive
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("experiment %s: unexpected provider error", experiment_id)
        outcome = dict(
            status=STATUS_FAILED,
            output=None,
            error_message="The model execution failed unexpectedly.",
        )

    # --- transaction 2: result --------------------------------------
    fresh = repo.get_experiment_by_id(db, experiment_id)
    assert fresh is not None
    repo.apply_result(
        db,
        fresh,
        status=str(outcome["status"]),
        executed_at=dt.datetime.now(dt.timezone.utc),
        response_time_ms=elapsed_ms,
        output=outcome["output"],
        error_message=outcome["error_message"],
    )
    db.commit()
    return _reload_read(db, experiment_id)


# --------------------------------------------------------------------------- #
# Score / notes                                                             #
# --------------------------------------------------------------------------- #
def update_experiment(
    db: Session,
    experiment_id: uuid.UUID,
    *,
    current_user: User,
    data: ExperimentScoreRequest,
) -> ExperimentRead:
    experiment = repo.get_experiment_by_id(db, experiment_id)
    if experiment is None:
        raise NotFoundError("Experiment not found.")
    _assert_owner(experiment.version.prompt, current_user)

    fields = data.model_fields_set
    if not fields:
        return _to_read(experiment)

    try:
        repo.update_score_notes(
            db,
            experiment,
            score=data.score,
            notes=data.notes,
            set_score="score" in fields,
            set_notes="notes" in fields,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("update_experiment failed; rolled back")
        raise
    return _reload_read(db, experiment_id)


# --------------------------------------------------------------------------- #
# Retrieval                                                                 #
# --------------------------------------------------------------------------- #
def list_for_prompt(
    db: Session, prompt_id: uuid.UUID, *, current_user: User
) -> ExperimentListResponse:
    prompt = prompt_repo.get_prompt_by_id(db, prompt_id)
    if prompt is None:
        raise NotFoundError("Prompt not found.")
    _assert_viewable(prompt, current_user)
    items = [_to_read(e) for e in repo.list_for_prompt(db, prompt_id)]
    return ExperimentListResponse(items=items, total=len(items))


def list_for_version(
    db: Session,
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
    *,
    current_user: User,
) -> ExperimentListResponse:
    prompt = prompt_repo.get_prompt_by_id(db, prompt_id)
    if prompt is None:
        raise NotFoundError("Prompt not found.")
    _assert_viewable(prompt, current_user)
    if not any(v.version_id == version_id for v in prompt.versions):
        raise NotFoundError("Version not found.")
    items = [
        _to_read(e) for e in repo.list_for_version(db, prompt_id, version_id)
    ]
    return ExperimentListResponse(items=items, total=len(items))


def list_models(db: Session) -> list[ModelRead]:
    """All model records, each flagged with whether execution is configured."""

    out: list[ModelRead] = []
    for model in model_repo.list_all(db):
        provider = get_provider(model.provider)
        out.append(
            ModelRead(
                model_id=model.model_id,
                name=model.name,
                provider=model.provider,
                created_at=model.created_at,
                execution_configured=bool(provider and provider.is_configured()),
            )
        )
    return out


def get_experiment(
    db: Session, experiment_id: uuid.UUID, *, current_user: User
) -> ExperimentRead:
    experiment = repo.get_experiment_by_id(db, experiment_id)
    if experiment is None:
        raise NotFoundError("Experiment not found.")
    # Authorize through the owning prompt — an experiment id cannot bypass it.
    prompt = experiment.version.prompt
    if not (prompt.user_id == current_user.user_id or prompt.is_public):
        raise NotFoundError("Experiment not found.")
    return _to_read(experiment)
