"""Neo4j driver lifecycle — one driver per process, created lazily.

The password comes only from configuration and is never logged or returned.
"""

from __future__ import annotations

import logging

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.core.config import get_settings

logger = logging.getLogger("promptdna")

_driver: Driver | None = None


class GraphUnavailable(Exception):
    """Neo4j is disabled or unreachable. The core app is unaffected."""


def _require_config() -> tuple[str, str, str, str]:
    s = get_settings()
    if not s.neo4j_enabled:
        raise GraphUnavailable("The graph projection (Neo4j) is not enabled.")
    if not s.neo4j_uri or not s.neo4j_password:
        raise GraphUnavailable("Neo4j is not configured on this server.")
    return s.neo4j_uri, s.neo4j_username, s.neo4j_password, s.neo4j_database


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        uri, user, password, _db = _require_config()
        _driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            # Traversal queries legitimately reference relationship types that
            # may not exist yet (e.g. FORKED_FROM before any fork is projected);
            # silence the resulting "UnknownRelationshipType" notifications.
            notifications_min_severity="OFF",
        )
    return _driver


def get_database() -> str:
    return get_settings().neo4j_database


def verify_connectivity() -> None:
    """Raise :class:`GraphUnavailable` if Neo4j cannot be reached."""

    try:
        get_driver().verify_connectivity()
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        # Never surface the driver exception (it can echo the URI).
        logger.warning("Neo4j connectivity check failed: %s", type(exc).__name__)
        raise GraphUnavailable("The graph service is currently unavailable.") from None


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
    _driver = None
