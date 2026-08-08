import pytest
from chronicle.core import (
    ChronicleEngine,
    MemoryNotFoundError,
    ProjectNotFoundError,
)
from chronicle.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def engine():
    db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db)
    return ChronicleEngine(sessionmaker(bind=db))


def test_create_project_and_get(engine):
    project = engine.create_project(name="demo", description="test project")
    assert project.name == "demo"
    assert project.description == "test project"

    fetched = engine.get_project(project.id)
    assert fetched is not None
    assert fetched.id == project.id
    assert fetched.name == "demo"


def test_get_project_missing_returns_none(engine):
    assert engine.get_project("missing") is None


def test_create_memory_creates_first_version(engine):
    project = engine.create_project(name="demo")

    memory = engine.create_memory(
        project_id=project.id, content="first", type="fact", context="ctx"
    )

    assert memory.project_id == project.id
    assert memory.type == "fact"
    assert len(memory.versions) == 1
    version = memory.versions[0]
    assert version.sequence == 1
    assert version.content == "first"
    assert version.context == "ctx"


def test_create_memory_unknown_project_raises(engine):
    with pytest.raises(ProjectNotFoundError):
        engine.create_memory(project_id="missing", content="first")


def test_create_version_appends_immutable_history(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1")

    version2 = engine.create_version(memory_id=memory.id, content="v2", context="new")

    assert version2.sequence == 2
    assert version2.content == "v2"

    fetched = engine.get_memory(memory.id)
    assert fetched is not None
    assert [v.sequence for v in fetched.versions] == [1, 2]
    assert [v.content for v in fetched.versions] == ["v1", "v2"]
    assert fetched.versions[-1].id == version2.id


def test_create_version_unknown_memory_raises(engine):
    with pytest.raises(MemoryNotFoundError):
        engine.create_version(memory_id="missing", content="v2")


def test_update_memory_changes_attribute_without_new_version(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1")

    updated = engine.update_memory(memory_id=memory.id, type="decision")

    assert updated.type == "decision"
    assert updated.versions is not None
    assert len(updated.versions) == 1
    assert updated.versions[0].content == "v1"


def test_update_memory_omitted_type_is_unchanged(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1", type="fact")

    updated = engine.update_memory(memory_id=memory.id)

    assert updated.type == "fact"


def test_update_memory_unknown_memory_raises(engine):
    with pytest.raises(MemoryNotFoundError):
        engine.update_memory(memory_id="missing", type="fact")


def test_list_memories_orders_by_creation(engine):
    project = engine.create_project(name="demo")
    first = engine.create_memory(project_id=project.id, content="a")
    second = engine.create_memory(project_id=project.id, content="b")

    memories = engine.list_memories(project_id=project.id)

    assert [m.id for m in memories] == [first.id, second.id]


def test_list_memories_unknown_project_is_empty(engine):
    assert engine.list_memories(project_id="missing") == []


# ------------------------------------------------------------------
# Snapshot tests
# ------------------------------------------------------------------


def test_create_snapshot(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    snapshot = engine.create_snapshot(project_id=project.id, message="initial state")

    assert snapshot.project_id == project.id
    assert snapshot.message == "initial state"
    assert len(snapshot.members) == 1
    assert snapshot.members[0].memory_version_id == memory.versions[0].id
    assert len(snapshot.snapshot_relationships) == 0


def test_create_snapshot_unknown_project_raises(engine):
    with pytest.raises(ProjectNotFoundError):
        engine.create_snapshot(project_id="missing")


def test_create_snapshot_captures_current_versions(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1")
    version2 = engine.create_version(memory_id=memory.id, content="v2")

    snapshot = engine.create_snapshot(project_id=project.id)

    assert len(snapshot.members) == 1
    assert snapshot.members[0].memory_version_id == version2.id


def test_create_snapshot_captures_relationships(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")
    rel = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="caused_by",
    )

    snapshot = engine.create_snapshot(project_id=project.id)

    assert len(snapshot.snapshot_relationships) == 1
    assert snapshot.snapshot_relationships[0].relationship_id == rel.id
    assert snapshot.snapshot_relationships[0].from_memory_id == mem_a.id
    assert snapshot.snapshot_relationships[0].to_memory_id == mem_b.id
    assert snapshot.snapshot_relationships[0].type == "caused_by"


def test_create_snapshot_empty_project(engine):
    project = engine.create_project(name="empty")

    snapshot = engine.create_snapshot(project_id=project.id)

    assert snapshot.project_id == project.id
    assert len(snapshot.members) == 0
    assert len(snapshot.snapshot_relationships) == 0


def test_get_snapshot(engine):
    project = engine.create_project(name="demo")
    created = engine.create_snapshot(project_id=project.id, message="test")

    fetched = engine.get_snapshot(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.message == "test"


def test_get_snapshot_unknown_returns_none(engine):
    assert engine.get_snapshot("missing") is None


def test_list_snapshots_returns_ordered(engine):
    project = engine.create_project(name="demo")
    first = engine.create_snapshot(project_id=project.id, message="first")
    second = engine.create_snapshot(project_id=project.id, message="second")

    snapshots = engine.list_snapshots(project_id=project.id)

    assert [s.id for s in snapshots] == [first.id, second.id]


def test_list_snapshots_unknown_project_is_empty(engine):
    assert engine.list_snapshots(project_id="missing") == []


def test_snapshot_is_immutable(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1")
    snapshot = engine.create_snapshot(project_id=project.id)

    engine.create_version(memory_id=memory.id, content="v2")

    fetched = engine.get_snapshot(snapshot.id)
    assert len(fetched.members) == 1
    assert fetched.members[0].memory_version_id == memory.versions[0].id
