"""Graph traversal response schemas.

Public identifiers are always the PostgreSQL ``prompt_id``. Neo4j internal node
ids, credentials, and driver objects are never exposed.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

RelationshipType = Literal["DERIVED_FROM", "FORKED_FROM", "DEPENDS_ON"]
Direction = Literal["incoming", "outgoing"]


class GraphRelationship(BaseModel):
    #: relationship type (for `related`); for ancestor/descendant lists the
    #: path may traverse either lineage type — see `rel_types`.
    type: RelationshipType | None = None
    #: for `related`: whether the edge points away from (outgoing) or toward
    #: (incoming) the subject prompt.
    direction: Direction | None = None
    #: the connected prompt (PostgreSQL id + authoritative title)
    prompt_id: uuid.UUID
    title: str
    #: hops from the subject prompt
    depth: int
    #: for multi-hop lineage results: the relationship types along the path
    rel_types: list[str] | None = None


class GraphResponse(BaseModel):
    prompt_id: uuid.UUID
    title: str
    #: what this list represents: "ancestors" | "descendants" | "dependencies" | "related"
    kind: str
    relationships: list[GraphRelationship]
