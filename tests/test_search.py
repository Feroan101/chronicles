import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from chronicle.core import ChronicleEngine, SearchQueryError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def store(tmp_path: Path):
    """A real Chronicle store migrated to the latest revision on a temp file."""
    db_path = tmp_path / "chronicle.db"
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")
    db = create_engine(f"sqlite:///{db_path}")
    return db_path, ChronicleEngine(sessionmaker(bind=db))


@pytest.fixture()
def engine(store):
    return store[1]


@pytest.fixture()
def project(engine):
    return engine.create_project(name="demo")


def _search(engine, query, project_id=None):
    return engine.search(query=query, project_id=project_id)


def test_search_finds_matching_content(engine, project):
    memory = engine.create_memory(project_id=project.id, content="The build uses Makefiles")

    results = _search(engine, "Makefiles")

    assert len(results) == 1
    assert results[0].memory.id == memory.id
    assert results[0].version.content == "The build uses Makefiles"
    assert results[0].version.sequence == 1


def test_search_does_not_return_non_matching_content(engine, project):
    engine.create_memory(project_id=project.id, content="The build uses Makefiles")

    assert _search(engine, "nonexistent-topic") == []
    assert _search(engine, "docker") == []


def test_search_returns_each_memory_at_most_once(engine, project):
    memory = engine.create_memory(
        project_id=project.id, content="Handles authentication and sessions"
    )
    engine.create_version(memory_id=memory.id, content="Handles authentication tokens")

    results = _search(engine, "authentication")

    assert len(results) == 1
    assert results[0].memory.id == memory.id
    assert results[0].version.sequence == 2


def test_search_does_not_return_historical_versions(engine, project):
    memory = engine.create_memory(project_id=project.id, content="Uses Flask")
    engine.create_version(memory_id=memory.id, content="Uses FastAPI")

    flask_results = _search(engine, "Flask")
    fastapi_results = _search(engine, "FastAPI")

    assert flask_results == []
    assert len(fastapi_results) == 1
    assert fastapi_results[0].memory.id == memory.id
    assert fastapi_results[0].version.sequence == 2
    assert fastapi_results[0].version.content == "Uses FastAPI"


def test_new_version_changes_what_is_searchable(engine, project):
    memory = engine.create_memory(project_id=project.id, content="Pins to Python 3.12")

    assert len(_search(engine, "3.12")) == 1
    assert _search(engine, "3.13") == []

    engine.create_version(memory_id=memory.id, content="Pins to Python 3.13")

    assert _search(engine, "3.12") == []
    assert len(_search(engine, "3.13")) == 1


def test_search_project_filtering(engine):
    project_a = engine.create_project(name="a")
    project_b = engine.create_project(name="b")
    memory_a = engine.create_memory(project_id=project_a.id, content="database schema notes")
    memory_b = engine.create_memory(project_id=project_b.id, content="database schema notes")

    in_a = _search(engine, "schema", project_id=project_a.id)
    in_b = _search(engine, "schema", project_id=project_b.id)

    assert [r.memory.id for r in in_a] == [memory_a.id]
    assert [r.memory.id for r in in_b] == [memory_b.id]


def test_search_across_projects_without_filter(engine):
    project_a = engine.create_project(name="a")
    project_b = engine.create_project(name="b")
    memory_a = engine.create_memory(project_id=project_a.id, content="database schema notes")
    memory_b = engine.create_memory(project_id=project_b.id, content="database schema notes")

    results = _search(engine, "schema")

    assert {r.memory.id for r in results} == {memory_a.id, memory_b.id}


def test_search_empty_query_raises(engine):
    for query in ("", "   ", "\t"):
        with pytest.raises(SearchQueryError):
            _search(engine, query)


def test_search_invalid_fts_query_raises(engine, project):
    engine.create_memory(project_id=project.id, content="something searchable")

    with pytest.raises(SearchQueryError):
        _search(engine, '"unterminated')


def test_search_does_not_modify_data(store, project):
    db_path, engine = store
    engine.create_memory(project_id=project.id, content="an important fact")

    def snapshot():
        con = sqlite3.connect(db_path)
        try:
            tables = ["memories", "memory_versions", "search_index", "projects"]
            return {table: list(con.execute(f"SELECT * FROM {table}")) for table in tables}
        finally:
            con.close()

    before = snapshot()
    results = _search(engine, "important")
    assert len(results) == 1
    after = snapshot()

    assert before == after


def test_result_includes_memory_type_and_context(engine, project):
    memory = engine.create_memory(
        project_id=project.id, content="decision knowledge", type="decision", context="when merging"
    )

    results = _search(engine, "decision")

    assert len(results) == 1
    result = results[0]
    assert result.memory.id == memory.id
    assert result.memory.type == "decision"
    assert result.version.context == "when merging"
    assert result.version.sequence == 1


def test_fts_index_populated_after_migration(store, project):
    db_path, engine = store
    engine.create_memory(project_id=project.id, content="indexed content one")
    engine.create_memory(project_id=project.id, content="indexed content two")

    con = sqlite3.connect(db_path)
    try:
        index_rows = con.execute("SELECT count(*) FROM search_index").fetchone()[0]
        version_rows = con.execute("SELECT count(*) FROM memory_versions").fetchone()[0]
        indexed_columns = {row[1] for row in con.execute("PRAGMA table_info(search_index)")}
    finally:
        con.close()

    assert index_rows == version_rows == 2
    assert {"memory_id", "memory_version_id", "content"} <= indexed_columns


def test_migration_backfills_existing_versions(tmp_path: Path):
    db_path = tmp_path / "chronicle.db"
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "4cd6c8553ab4")

    db = create_engine(f"sqlite:///{db_path}")
    with db.begin() as con:
        con.execute(
            text(
                "INSERT INTO projects (id, name, created_at) "
                "VALUES ('p1', 'demo', '2026-01-01 00:00:00')"
            )
        )
        con.execute(
            text(
                "INSERT INTO memories (id, project_id, type, created_at) "
                "VALUES ('m1', 'p1', NULL, '2026-01-01 00:00:00')"
            )
        )
        con.execute(
            text(
                "INSERT INTO memory_versions (id, memory_id, sequence, content, created_at) "
                "VALUES ('v1', 'm1', 1, 'pre existing content', '2026-01-01 00:00:00')"
            )
        )
    command.upgrade(cfg, "head")

    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT memory_id, memory_version_id, content FROM search_index"
        ).fetchall()
    finally:
        con.close()

    assert rows == [("m1", "v1", "pre existing content")]


def test_newly_created_memory_is_searchable(engine, project):
    engine.create_memory(project_id=project.id, content="deploy via kubernetes")

    results = _search(engine, "kubernetes")

    assert len(results) == 1
    assert results[0].version.content == "deploy via kubernetes"


def test_newly_created_version_is_searchable(engine, project):
    memory = engine.create_memory(project_id=project.id, content="initial state")
    engine.create_version(memory_id=memory.id, content="expanded with telemetry details")

    results = _search(engine, "telemetry")

    assert len(results) == 1
    assert results[0].memory.id == memory.id
    assert results[0].version.sequence == 2
    assert results[0].version.content == "expanded with telemetry details"


def test_search_is_case_insensitive(engine, project):
    engine.create_memory(project_id=project.id, content="DEPLOYMENT checklist")

    assert len(_search(engine, "deployment")) == 1
    assert len(_search(engine, "Deployment")) == 1
