"""Graph API business logic = PostgreSQL authorization + Neo4j traversal.

Neo4j must never bypass PostgreSQL authorization. Every graph request:

1. verifies the caller may VIEW the subject prompt in PostgreSQL (else 404),
2. runs the Neo4j traversal,
3. **filters every returned node through PostgreSQL visibility** (owner or
   ``is_public``) — a private prompt the caller cannot see is dropped from the
   result, even if the graph connects to it,
4. takes each node's ``title`` from PostgreSQL (the system of record), which
   also drops any Neo4j node that no longer exists in PostgreSQL.

If Neo4j is disabled/unreachable, graph endpoints return 503 — the rest of the
API (lexical search, semantic search, experiments, …) is unaffected.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import NotFoundError, ServiceUnavailableError
from app.core.config import get_settings
from app.db.models import Prompt, User
from app.graph import service as graph
from app.graph.client import GraphUnavailable
from app.repositories import prompt as prompt_repo
from app.schemas.graph import GraphRelationship, GraphResponse

logger = logging.getLogger("promptdna")


def _require_enabled() -> None:
    if not get_settings().neo4j_enabled:
        raise ServiceUnavailableError(
            "The knowledge graph (Neo4j) is not enabled on this server."
        )


def _load_viewable(db: Session, prompt_id: uuid.UUID, user: User) -> Prompt:
    prompt = prompt_repo.get_prompt_by_id(db, prompt_id)
    if prompt is None or not (
        prompt.user_id == user.user_id or prompt.is_public
    ):
        raise NotFoundError("Prompt not found.")
    return prompt


def _viewable_titles(
    db: Session, ids: Iterable[uuid.UUID], user: User
) -> dict[uuid.UUID, str]:
    """PostgreSQL is authoritative: return {prompt_id: title} for only the ids
    that exist AND the caller may view."""

    id_list = list({i for i in ids})
    if not id_list:
        return {}
    rows = db.execute(
        select(Prompt.prompt_id, Prompt.title).where(
            Prompt.prompt_id.in_(id_list),
            (Prompt.user_id == user.user_id) | Prompt.is_public.is_(True),
        )
    ).all()
    return {r.prompt_id: r.title for r in rows}


def _project(
    db: Session,
    subject: Prompt,
    user: User,
    kind: str,
    rows: list[dict],
) -> GraphResponse:
    ids = [uuid.UUID(str(r["prompt_id"])) for r in rows]
    titles = _viewable_titles(db, ids, user)
    rels: list[GraphRelationship] = []
    for r in rows:
        pid = uuid.UUID(str(r["prompt_id"]))
        if pid not in titles:  # not in PostgreSQL or not viewable -> drop
            continue
        rels.append(
            GraphRelationship(
                type=r.get("type"),
                direction=r.get("direction"),
                prompt_id=pid,
                title=titles[pid],  # authoritative title
                depth=int(r.get("depth", 1)),
                rel_types=r.get("rel_types"),
            )
        )
    return GraphResponse(
        prompt_id=subject.prompt_id,
        title=subject.title,
        kind=kind,
        relationships=rels,
    )


def _traverse(
    db: Session,
    prompt_id: uuid.UUID,
    *,
    current_user: User,
    kind: str,
    fn,
    **kw,
) -> GraphResponse:
    _require_enabled()
    subject = _load_viewable(db, prompt_id, current_user)
    try:
        rows = fn(str(prompt_id), **kw)
    except GraphUnavailable as exc:
        logger.info("graph traversal unavailable: %s", exc)
        raise ServiceUnavailableError(str(exc)) from None
    return _project(db, subject, current_user, kind, rows)


def ancestors(db, prompt_id, *, current_user, depth=10) -> GraphResponse:
    return _traverse(db, prompt_id, current_user=current_user, kind="ancestors",
                     fn=graph.ancestors, max_depth=depth)


def descendants(db, prompt_id, *, current_user, depth=10) -> GraphResponse:
    return _traverse(db, prompt_id, current_user=current_user, kind="descendants",
                     fn=graph.descendants, max_depth=depth)


def dependencies(db, prompt_id, *, current_user, depth=10) -> GraphResponse:
    return _traverse(db, prompt_id, current_user=current_user, kind="dependencies",
                     fn=graph.dependencies, max_depth=depth)


def related(db, prompt_id, *, current_user) -> GraphResponse:
    return _traverse(db, prompt_id, current_user=current_user, kind="related",
                     fn=graph.related)


# --------------------------------------------------------------------------- #
# Best-effort projection hook (called AFTER the PostgreSQL commit)           #
# --------------------------------------------------------------------------- #
def project_prompt_after_commit(
    prompt_id: uuid.UUID, title: str, parent_prompt_id: uuid.UUID | None
) -> None:
    """Eventual consistency: PostgreSQL is already committed. Project the node
    (and the DERIVED_FROM edge if there is a parent) to Neo4j. Any failure is
    logged and swallowed — PostgreSQL is never rolled back for Neo4j."""

    if not get_settings().neo4j_enabled:
        return
    try:
        graph.merge_prompt_node(str(prompt_id), title)
        if parent_prompt_id is not None:
            graph.merge_relationship(
                str(prompt_id), str(parent_prompt_id), "DERIVED_FROM"
            )
    except Exception:  # noqa: BLE001 - eventual consistency, never propagate
        logger.warning(
            "Neo4j projection for prompt %s failed (will reconcile on next sync)",
            prompt_id,
        )
