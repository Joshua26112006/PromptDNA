"""Phase 1 database schema tests — require real PostgreSQL (see conftest.py).

Covers the 15 checks mandated by the Phase 1 spec plus a few closely-related
extras (status CHECK, created_by RESTRICT, timezone-aware timestamps).
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Collection,
    Experiment,
    Model,
    Prompt,
    PromptCollection,
    PromptTag,
    Tag,
    User,
    Version,
)

EXPECTED_TABLES = {
    "users",
    "prompts",
    "versions",
    "models",
    "experiments",
    "tags",
    "collections",
    "prompt_tags",
    "prompt_collections",
}

EXPECTED_PKS = {
    "users": ["user_id"],
    "prompts": ["prompt_id"],
    "versions": ["version_id"],
    "models": ["model_id"],
    "experiments": ["experiment_id"],
    "tags": ["tag_id"],
    "collections": ["collection_id"],
    "prompt_tags": ["prompt_id", "tag_id"],
    "prompt_collections": ["prompt_id", "collection_id"],
}

# (table, local_cols) -> (referred_table, referred_cols, ondelete)
EXPECTED_FKS = {
    ("prompts", ("user_id",)): ("users", ("user_id",), "CASCADE"),
    ("prompts", ("parent_prompt_id",)): ("prompts", ("prompt_id",), "SET NULL"),
    ("versions", ("prompt_id",)): ("prompts", ("prompt_id",), "CASCADE"),
    ("versions", ("created_by",)): ("users", ("user_id",), "RESTRICT"),
    ("experiments", ("version_id",)): ("versions", ("version_id",), "CASCADE"),
    ("experiments", ("model_id",)): ("models", ("model_id",), "RESTRICT"),
    ("collections", ("user_id",)): ("users", ("user_id",), "CASCADE"),
    ("prompt_tags", ("prompt_id",)): ("prompts", ("prompt_id",), "CASCADE"),
    ("prompt_tags", ("tag_id",)): ("tags", ("tag_id",), "CASCADE"),
    ("prompt_collections", ("prompt_id",)): ("prompts", ("prompt_id",), "CASCADE"),
    ("prompt_collections", ("collection_id",)): (
        "collections",
        ("collection_id",),
        "CASCADE",
    ),
}


# --------------------------------------------------------------------------- #
# Row factories                                                              #
# --------------------------------------------------------------------------- #
def _sfx() -> str:
    return uuid.uuid4().hex[:8]


def mk_user(db: Session, **kw) -> User:
    u = User(
        name=kw.get("name", "Test User"),
        email=kw.get("email", f"user-{_sfx()}@promptdna.test"),
        password_hash=kw.get("password_hash", "placeholder-hash"),
    )
    db.add(u)
    db.flush()
    return u


def mk_prompt(db: Session, owner: User, **kw) -> Prompt:
    p = Prompt(
        user_id=owner.user_id,
        title=kw.get("title", "Test Prompt"),
        description=kw.get("description"),
        purpose=kw.get("purpose"),
        parent_prompt_id=kw.get("parent_prompt_id"),
        is_public=kw.get("is_public", False),
    )
    db.add(p)
    db.flush()
    return p


def mk_version(db: Session, prompt: Prompt, author: User, number: int = 1, **kw) -> Version:
    v = Version(
        prompt_id=prompt.prompt_id,
        version_number=number,
        content=kw.get("content", "some prompt content"),
        change_summary=kw.get("change_summary"),
        created_by=author.user_id,
    )
    db.add(v)
    db.flush()
    return v


def mk_model(db: Session, **kw) -> Model:
    m = Model(
        name=kw.get("name", f"Model-{_sfx()}"),
        provider=kw.get("provider", "TestProvider"),
    )
    db.add(m)
    db.flush()
    return m


def mk_experiment(db: Session, version: Version, model: Model, **kw) -> Experiment:
    e = Experiment(
        version_id=version.version_id,
        model_id=model.model_id,
        response_time_ms=kw.get("response_time_ms"),
        score=kw.get("score"),
        output=kw.get("output"),
        notes=kw.get("notes"),
        status=kw.get("status", "PENDING"),
        error_message=kw.get("error_message"),
    )
    db.add(e)
    db.flush()
    return e


def mk_tag(db: Session, name: str | None = None) -> Tag:
    t = Tag(name=name or f"tag-{_sfx()}")
    db.add(t)
    db.flush()
    return t


def mk_collection(db: Session, owner: User, **kw) -> Collection:
    c = Collection(
        user_id=owner.user_id,
        name=kw.get("name", "Test Collection"),
        description=kw.get("description"),
    )
    db.add(c)
    db.flush()
    return c


# --------------------------------------------------------------------------- #
# 1–4  structural checks (introspection)                                     #
# --------------------------------------------------------------------------- #
def test_all_expected_tables_exist(pg_engine):
    names = set(inspect(pg_engine).get_table_names())
    assert EXPECTED_TABLES <= names, EXPECTED_TABLES - names


def test_primary_keys_exist(pg_engine):
    insp = inspect(pg_engine)
    for table, cols in EXPECTED_PKS.items():
        pk = insp.get_pk_constraint(table)
        assert pk["constrained_columns"] == cols, (table, pk)


def test_foreign_keys_exist_with_delete_rules(pg_engine):
    insp = inspect(pg_engine)
    seen: dict[tuple[str, tuple[str, ...]], tuple] = {}
    for table in EXPECTED_TABLES:
        for fk in insp.get_foreign_keys(table):
            key = (table, tuple(fk["constrained_columns"]))
            seen[key] = (
                fk["referred_table"],
                tuple(fk["referred_columns"]),
                (fk.get("options") or {}).get("ondelete", "NO ACTION").upper(),
            )
    for key, expected in EXPECTED_FKS.items():
        assert key in seen, f"missing FK {key}"
        assert seen[key] == expected, (key, seen[key], expected)


def test_expected_unique_constraints_present(pg_engine):
    insp = inspect(pg_engine)

    def uniques(table: str) -> list[list[str]]:
        out = [uc["column_names"] for uc in insp.get_unique_constraints(table)]
        # unique indexes count too
        out += [
            ix["column_names"]
            for ix in insp.get_indexes(table)
            if ix.get("unique")
        ]
        return out

    assert ["email"] in uniques("users")
    assert ["name"] in uniques("models")
    assert ["name"] in uniques("tags")
    assert ["prompt_id", "version_number"] in uniques("versions")


def test_justified_secondary_indexes_exist(pg_engine):
    insp = inspect(pg_engine)
    expected = {
        "prompts": {"ix_prompts_user_id", "ix_prompts_parent_prompt_id"},
        "versions": {"ix_versions_created_by"},
        "experiments": {
            "ix_experiments_version_id",
            "ix_experiments_model_id",
            "ix_experiments_executed_at",
        },
        "collections": {"ix_collections_user_id"},
        "prompt_tags": {"ix_prompt_tags_tag_id"},
        "prompt_collections": {"ix_prompt_collections_collection_id"},
    }
    for table, names in expected.items():
        present = {ix["name"] for ix in insp.get_indexes(table)}
        assert names <= present, (table, names - present)


# --------------------------------------------------------------------------- #
# 4  unique constraints actually reject duplicates                           #
# --------------------------------------------------------------------------- #
def test_duplicate_email_rejected(db):
    mk_user(db, email="dup@promptdna.test")
    with pytest.raises(IntegrityError):
        mk_user(db, email="dup@promptdna.test")


def test_duplicate_model_name_rejected(db):
    mk_model(db, name="DuplicateModel")
    with pytest.raises(IntegrityError):
        mk_model(db, name="DuplicateModel")


def test_duplicate_tag_name_rejected(db):
    mk_tag(db, "DuplicateTag")
    with pytest.raises(IntegrityError):
        mk_tag(db, "DuplicateTag")


# --------------------------------------------------------------------------- #
# 5  duplicate version numbers per prompt rejected                           #
# --------------------------------------------------------------------------- #
def test_duplicate_version_number_for_same_prompt_rejected(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    mk_version(db, p, u, number=1)
    with pytest.raises(IntegrityError):
        mk_version(db, p, u, number=1)


def test_same_version_number_allowed_for_different_prompts(db):
    u = mk_user(db)
    p1 = mk_prompt(db, u)
    p2 = mk_prompt(db, u)
    mk_version(db, p1, u, number=1)
    mk_version(db, p2, u, number=1)  # must not raise


# --------------------------------------------------------------------------- #
# 6  version_number must be > 0                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [0, -1, -50])
def test_non_positive_version_number_rejected(db, bad):
    u = mk_user(db)
    p = mk_prompt(db, u)
    with pytest.raises(IntegrityError):
        mk_version(db, p, u, number=bad)


# --------------------------------------------------------------------------- #
# 7  experiment score must be within 0..10                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [-0.1, 10.1, 11, -1])
def test_experiment_score_out_of_range_rejected(db, bad):
    u = mk_user(db)
    p = mk_prompt(db, u)
    v = mk_version(db, p, u)
    m = mk_model(db)
    with pytest.raises(IntegrityError):
        mk_experiment(db, v, m, score=bad)


@pytest.mark.parametrize("ok", [0, 5, 10, 8.5])
def test_experiment_score_in_range_accepted(db, ok):
    u = mk_user(db)
    p = mk_prompt(db, u)
    v = mk_version(db, p, u)
    m = mk_model(db)
    mk_experiment(db, v, m, score=ok)  # must not raise


# --------------------------------------------------------------------------- #
# 8  negative response_time_ms rejected                                      #
# --------------------------------------------------------------------------- #
def test_negative_response_time_rejected(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    v = mk_version(db, p, u)
    m = mk_model(db)
    with pytest.raises(IntegrityError):
        mk_experiment(db, v, m, response_time_ms=-1)


def test_zero_response_time_accepted(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    v = mk_version(db, p, u)
    m = mk_model(db)
    mk_experiment(db, v, m, response_time_ms=0)


# --------------------------------------------------------------------------- #
# extra: status CHECK                                                        #
# --------------------------------------------------------------------------- #
def test_invalid_experiment_status_rejected(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    v = mk_version(db, p, u)
    m = mk_model(db)
    with pytest.raises(IntegrityError):
        mk_experiment(db, v, m, status="NOPE")


# --------------------------------------------------------------------------- #
# 9  user deletion cascades to prompts                                       #
# --------------------------------------------------------------------------- #
def test_user_delete_cascades_to_prompts(db):
    u = mk_user(db)
    mk_prompt(db, u)
    mk_prompt(db, u)
    db.execute(sa.delete(User).where(User.user_id == u.user_id))
    db.flush()
    remaining = db.scalar(
        sa.select(sa.func.count()).select_from(Prompt).where(Prompt.user_id == u.user_id)
    )
    assert remaining == 0


# --------------------------------------------------------------------------- #
# 10  prompt deletion cascades to versions                                   #
# --------------------------------------------------------------------------- #
def test_prompt_delete_cascades_to_versions(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    mk_version(db, p, u, number=1)
    mk_version(db, p, u, number=2)
    db.execute(sa.delete(Prompt).where(Prompt.prompt_id == p.prompt_id))
    db.flush()
    remaining = db.scalar(
        sa.select(sa.func.count()).select_from(Version).where(Version.prompt_id == p.prompt_id)
    )
    assert remaining == 0


# --------------------------------------------------------------------------- #
# 11  deleting a parent prompt nulls the child's parent_prompt_id            #
# --------------------------------------------------------------------------- #
def test_parent_prompt_delete_sets_child_parent_to_null(db):
    u = mk_user(db)
    parent = mk_prompt(db, u, title="parent")
    child = mk_prompt(db, u, title="child", parent_prompt_id=parent.prompt_id)
    db.execute(sa.delete(Prompt).where(Prompt.prompt_id == parent.prompt_id))
    db.flush()
    db.expire_all()
    still_there = db.get(Prompt, child.prompt_id)
    assert still_there is not None
    assert still_there.parent_prompt_id is None


# --------------------------------------------------------------------------- #
# 12  model deletion is RESTRICTed while experiments reference it            #
# --------------------------------------------------------------------------- #
def test_model_delete_restricted_when_referenced(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    v = mk_version(db, p, u)
    m = mk_model(db)
    mk_experiment(db, v, m, status="SUCCESS", score=5)
    with pytest.raises(IntegrityError):
        db.execute(sa.delete(Model).where(Model.model_id == m.model_id))
        db.flush()


# extra: versions.created_by is RESTRICTed
def test_version_author_delete_restricted(db):
    owner = mk_user(db)
    author = mk_user(db)  # different user authored the version
    p = mk_prompt(db, owner)
    mk_version(db, p, author, number=1)
    with pytest.raises(IntegrityError):
        db.execute(sa.delete(User).where(User.user_id == author.user_id))
        db.flush()


# --------------------------------------------------------------------------- #
# 13  deleting a tag removes prompt_tags rows but not the prompts            #
# --------------------------------------------------------------------------- #
def test_tag_delete_removes_links_not_prompts(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    t = mk_tag(db)
    db.add(PromptTag(prompt_id=p.prompt_id, tag_id=t.tag_id))
    db.flush()
    db.execute(sa.delete(Tag).where(Tag.tag_id == t.tag_id))
    db.flush()
    links = db.scalar(
        sa.select(sa.func.count()).select_from(PromptTag).where(PromptTag.tag_id == t.tag_id)
    )
    assert links == 0
    assert db.get(Prompt, p.prompt_id) is not None


# --------------------------------------------------------------------------- #
# 14  deleting a collection removes prompt_collections rows but not prompts  #
# --------------------------------------------------------------------------- #
def test_collection_delete_removes_links_not_prompts(db):
    u = mk_user(db)
    p = mk_prompt(db, u)
    c = mk_collection(db, u)
    db.add(PromptCollection(prompt_id=p.prompt_id, collection_id=c.collection_id))
    db.flush()
    db.execute(sa.delete(Collection).where(Collection.collection_id == c.collection_id))
    db.flush()
    links = db.scalar(
        sa.select(sa.func.count())
        .select_from(PromptCollection)
        .where(PromptCollection.collection_id == c.collection_id)
    )
    assert links == 0
    assert db.get(Prompt, p.prompt_id) is not None


# --------------------------------------------------------------------------- #
# 15  many-to-many relationships work in both directions                     #
# --------------------------------------------------------------------------- #
def test_many_to_many_prompt_tags_and_collections(db):
    u = mk_user(db)
    p1 = mk_prompt(db, u, title="p1")
    p2 = mk_prompt(db, u, title="p2")
    t1 = mk_tag(db)
    t2 = mk_tag(db)
    c1 = mk_collection(db, u, name="c1")
    c2 = mk_collection(db, u, name="c2")

    p1.tags.extend([t1, t2])
    p1.collections.extend([c1, c2])
    p2.collections.append(c1)
    db.flush()
    db.expire_all()

    p1r = db.get(Prompt, p1.prompt_id)
    assert {t.name for t in p1r.tags} == {t1.name, t2.name}
    assert {c.name for c in p1r.collections} == {"c1", "c2"}

    t1r = db.get(Tag, t1.tag_id)
    assert p1.prompt_id in {p.prompt_id for p in t1r.prompts}

    c1r = db.get(Collection, c1.collection_id)
    assert {p.prompt_id for p in c1r.prompts} == {p1.prompt_id, p2.prompt_id}


# --------------------------------------------------------------------------- #
# extra: timestamps are timezone-aware (TIMESTAMPTZ)                         #
# --------------------------------------------------------------------------- #
def test_timestamps_are_timezone_aware(db):
    u = mk_user(db)
    db.refresh(u)
    assert u.created_at.tzinfo is not None
    assert u.updated_at.tzinfo is not None
