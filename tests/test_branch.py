import pytest
from chronicle.core import (
    DEFAULT_BRANCH_NAME,
    BranchNameConflictError,
    BranchNotFoundError,
    ChronicleEngine,
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


def test_create_project_creates_default_branch(engine):
    project = engine.create_project(name="demo")
    branches = engine.list_branches(project.id)
    assert len(branches) == 1
    assert branches[0].is_default is True
    current = engine.get_current_branch(project.id)
    assert current.id == branches[0].id


def test_create_branch_fork_spreads_knowledge(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="shared knowledge")

    branch = engine.create_branch(project.id, name="experimental")
    assert branch.is_default is False
    assert branch.name == "experimental"

    default = engine.get_current_branch(project.id)
    items = engine.get_branch_knowledge(branch.id)
    assert len(items) == 1
    assert items[0].memory.id == engine.list_memories(project.id)[0].id

    shared_versions = {item.version.id for item in items}
    default_items = engine.get_branch_knowledge(default.id)
    default_versions = {item.version.id for item in default_items}
    assert shared_versions == default_versions


def test_branches_isolate_new_knowledge(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="on main")

    branch = engine.create_branch(project.id, name="experimental")
    engine.switch_branch(project.id, "experimental")
    engine.create_memory(project_id=project.id, content="on fork")

    main_branch = engine.get_current_branch(project.id)
    assert main_branch.id == branch.id

    fork_items = engine.get_branch_knowledge(branch.id)
    fork_content = {item.version.content for item in fork_items}
    assert fork_content == {"on main", "on fork"}

    default_branch = engine.get_branch_by_name(project.id, DEFAULT_BRANCH_NAME)
    assert default_branch is not None
    default_items = engine.get_branch_knowledge(default_branch.id)
    default_content = {item.version.content for item in default_items}
    assert default_content == {"on main"}

    visible = engine.list_memories(project.id, branch_id=branch.id)
    assert len(visible) == 2


def test_switch_branch_changes_current_branch(engine):
    project = engine.create_project(name="demo")
    branch = engine.create_branch(project.id, name="experimental")
    assert engine.get_current_branch(project.id).id != branch.id

    switched = engine.switch_branch(project.id, "experimental")
    assert switched.id == branch.id
    assert engine.get_current_branch(project.id).id == branch.id


def test_create_branch_name_conflict(engine):
    project = engine.create_project(name="demo")
    engine.create_branch(project.id, name="experimental")
    with pytest.raises(BranchNameConflictError):
        engine.create_branch(project.id, name="experimental")


def test_create_branch_unknown_source(engine):
    project = engine.create_project(name="demo")
    with pytest.raises(BranchNotFoundError):
        engine.create_branch(project.id, name="experimental", source_branch_id="missing")


def test_branch_unknown_project(engine):
    with pytest.raises(ProjectNotFoundError):
        engine.create_branch(project_id="missing", name="experimental")


def test_get_branch_knowledge_unknown_branch(engine):
    with pytest.raises(BranchNotFoundError):
        engine.get_branch_knowledge("missing")


def test_switch_branch_unknown_branch(engine):
    project = engine.create_project(name="demo")
    with pytest.raises(BranchNotFoundError):
        engine.switch_branch(project.id, "missing")


def test_create_memory_on_explicit_branch(engine):
    project = engine.create_project(name="demo")
    branch = engine.create_branch(project.id, name="feature")
    engine.create_memory(project_id=project.id, content="scoped", branch_id=branch.id)

    main_branch = engine.get_branch_by_name(project.id, DEFAULT_BRANCH_NAME)
    assert main_branch is not None
    main_content = {item.version.content for item in engine.get_branch_knowledge(main_branch.id)}
    assert main_content == set()

    feature_content = {item.version.content for item in engine.get_branch_knowledge(branch.id)}
    assert feature_content == {"scoped"}


def test_create_version_follows_memory_branch(engine):
    project = engine.create_project(name="demo")
    branch = engine.create_branch(project.id, name="feature")
    engine.switch_branch(project.id, "feature")
    memory = engine.create_memory(project_id=project.id, content="v1")

    engine.create_version(memory_id=memory.id, content="v2")
    version = engine.get_version(memory_id=memory.id, sequence=2)
    assert version is not None

    items = engine.get_branch_knowledge(branch.id)
    assert {item.version.content for item in items} == {"v2"}
    default = engine.get_branch_by_name(project.id, DEFAULT_BRANCH_NAME)
    assert default is not None
    assert engine.get_branch_knowledge(default.id) == []


def test_list_memories_scoped_to_branch(engine):
    project = engine.create_project(name="demo")
    branch = engine.create_branch(project.id, name="feature")
    engine.switch_branch(project.id, "feature")
    engine.create_memory(project_id=project.id, content="fork-only")

    default_branch = engine.get_branch_by_name(project.id, DEFAULT_BRANCH_NAME)
    assert default_branch is not None
    assert engine.list_memories(project.id, branch_id=default_branch.id) == []

    branch_visible = engine.list_memories(project.id, branch_id=branch.id)
    assert {item.versions[-1].content for item in branch_visible} == {"fork-only"}

    current = engine.list_memories(project.id)
    assert {item.versions[-1].content for item in current} == {"fork-only"}


def test_snapshot_captures_branch_state(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="on main")

    branch = engine.create_branch(project.id, name="feature")
    engine.switch_branch(project.id, "feature")
    engine.create_memory(project_id=project.id, content="fork-only")

    snapshot = engine.create_snapshot(project_id=project.id, branch_id=branch.id)
    assert snapshot.branch_id == branch.id
    assert len(snapshot.members) == 2

    main_branch = engine.get_branch_by_name(project.id, DEFAULT_BRANCH_NAME)
    assert main_branch is not None
    main_snapshot = engine.create_snapshot(project_id=project.id, branch_id=main_branch.id)
    assert len(main_snapshot.members) == 1


def test_memory_not_visible_from_other_branch(engine):
    project = engine.create_project(name="demo")
    branch = engine.create_branch(project.id, name="feature")
    memory = engine.create_memory(project_id=project.id, content="scoped", branch_id=branch.id)

    main_branch = engine.get_branch_by_name(project.id, DEFAULT_BRANCH_NAME)
    assert main_branch is not None
    main_items = engine.get_branch_knowledge(main_branch.id)
    assert all(item.memory.id != memory.id for item in main_items)
