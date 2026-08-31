"""Backfill embeddings for versions that don't have one.

    cd backend
    ./.venv/Scripts/python.exe scripts/generate_embeddings.py [--limit N] [--dry-run]

Uses the configured embedding provider (`EMBEDDING_PROVIDER`, default "mock") and
`DATABASE_URL`. Requires a PostgreSQL with the `vector` extension + migration
0002. Immutable versions never change content, so once a version has an
embedding it is skipped — this does not regenerate.
"""

from __future__ import annotations

import argparse
import sys

from app.core.config import get_settings
from app.db.session import build_engine
from app.embeddings.registry import get_embedding_provider
from app.repositories import version as repo


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill version embeddings.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    provider = get_embedding_provider()
    if not provider.is_configured():
        print("Embedding provider is not configured — aborting.", file=sys.stderr)
        return 2

    engine = build_engine()
    from sqlalchemy.orm import Session

    ok = failed = 0
    with Session(engine) as db:
        pending = repo.versions_missing_embedding(db, limit=args.limit)
        print(f"{len(pending)} version(s) without an embedding "
              f"(provider={provider.key}, model={provider.model_name}, "
              f"dim={provider.dimension}).")
        for version in pending:
            if args.dry_run:
                print(f"  would embed {version.version_id}")
                continue
            try:
                vec = provider.embed(
                    version.content,
                    timeout_s=get_settings().embedding_provider_timeout_s,
                )
                repo.set_embedding(
                    db, version, vector=vec, model_name=provider.model_name
                )
                db.commit()
                ok += 1
            except Exception as exc:  # noqa: BLE001 - report and continue
                db.rollback()
                failed += 1
                print(f"  FAILED {version.version_id}: {type(exc).__name__}",
                      file=sys.stderr)
    engine.dispose()
    print(f"done — {ok} embedded, {failed} failed"
          + (" (dry run)" if args.dry_run else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
