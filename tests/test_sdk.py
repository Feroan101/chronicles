import inspect
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from chronicle import Chronicle as ReexportedChronicle
from chronicle.api.schemas import (
    MemoryRead,
    MemoryVersionRead,
    ProjectRead,
    SearchHitRead,
)
from chronicle.core import (
    MemoryNotFoundError,
    MemoryVersionNotFoundError,
    ProjectNotFoundError,
    SearchQueryError,
)
from chronicle.sdk import UNSET, Chronicle
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def db_path(tmp_path: Path):
    """A migrated Chronicle store on a temp file, returning its path."""
    path = tmp_path / "chronicle.db"
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(cfg, "head")
    return path


@pytest.fixture()
def chronicle(db_path) -> Chronicle:
    return Chronicle(db_path=db_path)


@pytest.fixture()
def project_id(chronicle: Chronicle) -> str:
    return chronicle.create_project(name="demo").id


def _create_memory(chronicle: Chronicle, project_id: str, content: str, **kwargs) -> MemoryRead:
    return chronicle.create_memory(project_id=project_id, content=content, **kwargs)


# --- construction -----------------------------------------------------------


def test_construction_with_default_path(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store_dir = tmp_path / ".chronicle"
    store_dir.mkdir()
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{store_dir / 'chronicle.db'}")
    command.upgrade(cfg, "head")

    chronicle = Chronicle()

    project = chronicle.create_project(name="demo")

    assert project.id


def test_construction_with_explicit_db_path(db_path):
    chronicle = Chronicle(db_path=db_path)

    project = chronicle.create_project(name="demo")

    assert project.id


def test_construction_with_session_factory(db_path):
    db = create_engine(f"sqlite:///{db_path}")
    chronicle = Chronicle(session_factory=sessionmaker(bind=db))

    project = chronicle.create_project(name="demo")

    assert project.id


def test_construction_does_not_create_or_migrate_missing_store(tmp_path: Path):
    path = tmp_path / "unmigrated.db"

    chronicle = Chronicle(db_path=path)

    with pytest.raises(OperationalError):
        chronicle.create_project(name="demo")


def test_top_level_reexport():
    assert ReexportedChronicle is Chronicle


def test_unset_is_exported_and_singleton():
    assert UNSET is UNSET
    assert repr(UNSET) == "UNSET"


def test_all_methods_are_synchronous():
    for name in (
        "create_project",
        "get_project",
        "create_memory",
        "get_memory",
        "list_memories",
        "update_memory",
        "create_version",
        "search",
    ):
        member = inspect.getattr_static(Chronicle, name)
        assert not inspect.iscoroutinefunction(member), f"{name} must be sync"


# --- projects ---------------------------------------------------------------


def test_create_and_get_project(chronicle: Chronicle):
    created = chronicle.create_project(name="demo", description="x")

    assert isinstance(created, ProjectRead)
    assert created.name == "demo"
    assert created.description == "x"
    assert created.id
    assert created.created_at

    fetched = chronicle.get_project(created.id)

    assert fetched == created


def test_get_missing_project_raises(chronicle: Chronicle):
    with pytest.raises(ProjectNotFoundError) as exc:
        chronicle.get_project("missing")

    assert exc.value.project_id == "missing"


# --- memories ---------------------------------------------------------------


def test_create_and_get_memory(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "first", type="fact", context="ctx")

    assert isinstance(memory, MemoryRead)
    assert memory.project_id == project_id
    assert memory.type == "fact"
    assert len(memory.versions) == 1
    version = memory.versions[0]
    assert isinstance(version, MemoryVersionRead)
    assert version.sequence == 1
    assert version.content == "first"
    assert version.context == "ctx"

    fetched = chronicle.get_memory(memory.id)

    assert fetched == memory


def test_create_memory_unknown_project_raises(chronicle: Chronicle):
    with pytest.raises(ProjectNotFoundError):
        chronicle.create_memory(project_id="missing", content="x")


def test_get_missing_memory_raises(chronicle: Chronicle):
    with pytest.raises(MemoryNotFoundError) as exc:
        chronicle.get_memory("missing")

    assert exc.value.memory_id == "missing"


def test_list_memories_orders_by_creation(chronicle: Chronicle, project_id: str):
    first = _create_memory(chronicle, project_id, "a").id
    second = _create_memory(chronicle, project_id, "b").id

    memories = chronicle.list_memories(project_id)

    assert all(isinstance(m, MemoryRead) for m in memories)
    assert [m.id for m in memories] == [first, second]


def test_list_memories_unknown_project_returns_empty(chronicle: Chronicle):
    assert chronicle.list_memories("missing") == []


# --- versions ---------------------------------------------------------------


def test_create_version_appends_history(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "v1")

    version = chronicle.create_version(memory.id, "v2", context="new")

    assert isinstance(version, MemoryVersionRead)
    assert version.sequence == 2
    assert version.content == "v2"
    assert version.context == "new"

    fetched = chronicle.get_memory(memory.id)
    assert [v.sequence for v in fetched.versions] == [1, 2]


def test_create_version_unknown_memory_raises(chronicle: Chronicle):
    with pytest.raises(MemoryNotFoundError):
        chronicle.create_version("missing", "v2")


# --- update_memory ----------------------------------------------------------


def test_update_type(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "v1", type="fact")

    updated = chronicle.update_memory(memory.id, type="decision")

    assert isinstance(updated, MemoryRead)
    assert updated.type == "decision"
    assert len(updated.versions) == 1


def test_update_omitted_type_leaves_unchanged(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "v1", type="fact")

    updated = chronicle.update_memory(memory.id)

    assert updated.type == "fact"


def test_update_explicit_none_clears_type(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "v1", type="fact")

    updated = chronicle.update_memory(memory.id, type=None)

    assert updated.type is None


def test_update_explicit_unset_leaves_unchanged(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "v1", type="fact")

    updated = chronicle.update_memory(memory.id, type=UNSET)

    assert updated.type == "fact"


def test_update_unknown_memory_raises(chronicle: Chronicle):
    with pytest.raises(MemoryNotFoundError):
        chronicle.update_memory("missing", type="decision")


# --- search -----------------------------------------------------------------


def test_search_across_projects(chronicle: Chronicle, project_id: str):
    other = chronicle.create_project(name="other").id
    _create_memory(chronicle, project_id, "schema notes")
    _create_memory(chronicle, other, "schema notes")

    hits = chronicle.search("schema")

    assert len(hits) == 2
    assert all(isinstance(h, SearchHitRead) for h in hits)


def test_search_project_filter(chronicle: Chronicle, project_id: str):
    other = chronicle.create_project(name="other").id
    _create_memory(chronicle, project_id, "schema notes")
    _create_memory(chronicle, other, "schema notes")

    hits = chronicle.search("schema", project_id=project_id)

    assert len(hits) == 1
    assert hits[0].memory.project_id == project_id


def test_search_returns_current_version(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "Uses Flask")
    chronicle.create_version(memory.id, "Uses FastAPI")

    hits = chronicle.search("FastAPI")

    assert len(hits) == 1
    hit = hits[0]
    assert hit.memory.id == memory.id
    assert hit.version.sequence == 2
    assert hit.version.content == "Uses FastAPI"
    assert isinstance(hit.rank, float)


def test_search_empty_query_raises(chronicle: Chronicle):
    for query in ("", "   ", "\t"):
        with pytest.raises(SearchQueryError):
            chronicle.search(query)


def test_search_invalid_query_raises(chronicle: Chronicle):
    with pytest.raises(SearchQueryError):
        chronicle.search('"unterminated')


# --- read model contract ----------------------------------------------------


def test_returns_pydantic_read_models(chronicle: Chronicle, project_id: str):
    project = chronicle.create_project(name="another")
    memory = _create_memory(chronicle, project_id, "content")
    version = chronicle.create_version(memory.id, "updated")
    hits = chronicle.search("updated")

    for result in (project, memory, version, hits[0], chronicle.get_project(project.id)):
        assert isinstance(result, BaseModel)

    assert isinstance(chronicle.get_memory(memory.id).versions[0], MemoryVersionRead)


def test_does_not_expose_orm_objects(chronicle: Chronicle, project_id: str):
    project = chronicle.get_project(project_id)
    memory = chronicle.get_memory(_create_memory(chronicle, project_id, "x").id)
    version = chronicle.create_version(memory.id, "v2")
    hit = chronicle.search("v2")[0]

    for result in (project, memory, version, hit):
        assert not hasattr(result, "_sa_instance_state")
        assert result.__class__.__module__ == "chronicle.api.schemas"


# --- verification -----------------------------------------------------------


def test_verify_project(chronicle: Chronicle, project_id: str):
    _create_memory(chronicle, project_id, "knowledge", type="fact")

    report = chronicle.verify_project(project_id)

    assert report.scope == "project"
    assert report.scope_id == project_id
    assert report.passed is True
    assert report.has_failures is False
    assert len(report.results) > 0


def test_verify_project_unknown_project_raises(chronicle: Chronicle):
    with pytest.raises(ProjectNotFoundError):
        chronicle.verify_project("missing")


def test_verify_memory(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "knowledge", type="fact")

    report = chronicle.verify_memory(memory.id)

    assert report.scope == "memory"
    assert report.scope_id == memory.id
    assert report.passed is True


def test_verify_memory_unknown_memory_raises(chronicle: Chronicle):
    with pytest.raises(MemoryNotFoundError):
        chronicle.verify_memory("missing")


def test_verify_version(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "knowledge", context="ctx")

    report = chronicle.verify_version(memory.id, 1)

    assert report.scope == "version"
    assert report.scope_id == f"{memory.id}:1"
    assert report.passed is True
    checks = {r.check: r.outcome for r in report.results}
    assert checks["traceability"] == "verified"


def test_verify_version_unknown_sequence_raises(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "knowledge")

    with pytest.raises(MemoryVersionNotFoundError):
        chronicle.verify_version(memory.id, 99)


def test_verify_snapshot(chronicle: Chronicle, project_id: str):
    _create_memory(chronicle, project_id, "knowledge")
    snapshot = chronicle.create_snapshot(project_id)

    report = chronicle.verify_snapshot(snapshot.id)

    assert report.scope == "snapshot"
    assert report.scope_id == snapshot.id
    assert report.passed is True


def test_verify_does_not_modify_confidence(chronicle: Chronicle, project_id: str):
    memory = _create_memory(chronicle, project_id, "knowledge")
    chronicle.record_confidence(memory.id, 1, 0.7)

    chronicle.verify_project(project_id)

    confidence = chronicle.get_confidence(memory.id, 1)
    assert confidence.score == 0.7
