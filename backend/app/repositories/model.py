"""Data access for AI model records. No commits."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Model


def get_by_id(db: Session, model_id: uuid.UUID) -> Model | None:
    return db.get(Model, model_id)


def list_all(db: Session) -> Sequence[Model]:
    return db.scalars(select(Model).order_by(Model.name.asc())).all()
