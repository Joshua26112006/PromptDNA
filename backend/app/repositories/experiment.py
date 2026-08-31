"""Data access for experiments. No commits — the service owns transactions."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Experiment, Version


def add_experiment(
    db: Session,
    *,
    version_id: uuid.UUID,
    model_id: uuid.UUID,
    status: str,
    notes: str | None,
) -> Experiment:
    experiment = Experiment(
        version_id=version_id,
        model_id=model_id,
        status=status,
        notes=notes,
    )
    db.add(experiment)
    db.flush()
    return experiment


def get_experiment_by_id(db: Session, experiment_id: uuid.UUID) -> Experiment | None:
    """Load the experiment with its model + version + parent prompt (for authz)."""

    stmt = (
        select(Experiment)
        .where(Experiment.experiment_id == experiment_id)
        .options(
            joinedload(Experiment.model),
            joinedload(Experiment.version).joinedload(Version.prompt),
        )
    )
    return db.scalars(stmt).one_or_none()


def _base_query(prompt_id: uuid.UUID):
    return (
        select(Experiment)
        .join(Version, Version.version_id == Experiment.version_id)
        .where(Version.prompt_id == prompt_id)
        .options(
            joinedload(Experiment.model),
            selectinload(Experiment.version),
        )
        .order_by(Experiment.executed_at.desc())
    )


def list_for_prompt(db: Session, prompt_id: uuid.UUID) -> Sequence[Experiment]:
    return db.scalars(_base_query(prompt_id)).all()


def list_for_version(
    db: Session, prompt_id: uuid.UUID, version_id: uuid.UUID
) -> Sequence[Experiment]:
    stmt = _base_query(prompt_id).where(Experiment.version_id == version_id)
    return db.scalars(stmt).all()


def apply_result(
    db: Session,
    experiment: Experiment,
    *,
    status: str,
    executed_at: dt.datetime,
    response_time_ms: int | None,
    output: str | None = None,
    error_message: str | None = None,
) -> Experiment:
    experiment.status = status
    experiment.executed_at = executed_at
    experiment.response_time_ms = response_time_ms
    experiment.output = output
    experiment.error_message = error_message
    db.flush()
    return experiment


def update_score_notes(
    db: Session,
    experiment: Experiment,
    *,
    score: float | None,
    notes: str | None,
    set_score: bool,
    set_notes: bool,
) -> Experiment:
    if set_score:
        experiment.score = score
    if set_notes:
        experiment.notes = notes
    db.flush()
    return experiment
