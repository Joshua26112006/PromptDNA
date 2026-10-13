"""Register the local Ollama models in the ``models`` table (idempotent).

    cd backend
    PYTHONPATH=. ./.venv/Scripts/python.exe scripts/seed_local_models.py

LOCAL DEVELOPMENT ONLY. The application has no API for creating model rows, and
``models`` is reference data, so this inserts the rows through the ORM — never
deletes or renames anything, and reuses a row when the exact name exists.
Names match the Ollama tags exactly because the name is sent to the server as
the model id. provider = "openai": Ollama is reached through the existing
OpenAI-compatible provider (OPENAI_BASE_URL=http://localhost:11434/v1).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Model
from app.db.session import build_engine

LOCAL_MODELS = ["gemma3:4b", "qwen3:4b"]


def main() -> int:
    engine = build_engine()
    with Session(engine) as db:
        for name in LOCAL_MODELS:
            row = db.execute(select(Model).where(Model.name == name)).scalar_one_or_none()
            if row is None:
                row = Model(name=name, provider="openai")
                db.add(row)
                db.flush()
                print(f"created  {name}  provider=openai  model_id={row.model_id}")
            else:
                print(f"reused   {name}  provider={row.provider}  model_id={row.model_id}")
        db.commit()
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
