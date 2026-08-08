import pytest
from chronicle.core import (
    ChronicleEngine,
    GitContext,
    GitContextError,
    MemoryNotFoundError,
)
from chronicle.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def engine():
    db = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db)
    return ChronicleEngine(sessionmaker(bind=db))


def _make_project(engine: ChronicleEngine):
    return engine.create_project(name="demo")


# --- GitContext validation ---


def test_git_context_requires_at_least_one_field():
    with pytest.raises(GitContextError, match="at least one field"):
        GitContext()


def test_git_context_rejects_empty_branch():
    with pytest.raises(GitContextError, match="branch"):
        GitContext(branch="  ")


def test_git_context_rejects_empty_commit():
    with pytest.raises(GitContextError, match="commit"):
        GitContext(commit="")


def test_git_context_rejects_empty_description():
    with pytest.raises(GitContextError, match="description"):
        GitContext(description="  ")


def test_git_context_allows_single_branch():
    ctx = GitContext(branch="main")
    assert ctx.branch == "main"
    assert ctx.commit is None
    assert ctx.description is None


def test_git_context_allows_multiple_fields():
    ctx = GitContext(branch="main", commit="abc123", description="fix bug")
    assert ctx.branch == "main"
    assert ctx.commit == "abc123"
    assert ctx.description == "fix bug"


# --- create_memory with git_context ---


def test_create_memory_with_git_context(engine: ChronicleEngine):
    project = _make_project(engine)
    ctx = GitContext(branch="main", commit="abc123", description="init")

    memory = engine.create_memory(project_id=project.id, content="first", git_context=ctx)

    version = memory.versions[0]
    assert version.git_context is not None
    assert version.git_context["branch"] == "main"
    assert version.git_context["commit"] == "abc123"
    assert version.git_context["description"] == "init"
    assert len(version.evidence) == 3


def test_create_memory_with_partial_git_context(engine: ChronicleEngine):
    project = _make_project(engine)
    ctx = GitContext(commit="abc123")

    memory = engine.create_memory(project_id=project.id, content="first", git_context=ctx)

    version = memory.versions[0]
    assert version.git_context is not None
    assert version.git_context == {"commit": "abc123"}
    assert len(version.evidence) == 1


def test_create_memory_without_git_context(engine: ChronicleEngine):
    project = _make_project(engine)

    memory = engine.create_memory(project_id=project.id, content="first")

    version = memory.versions[0]
    assert version.git_context is None
    assert len(version.evidence) == 0


# --- create_version with git_context ---


def test_create_version_with_git_context(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(project_id=project.id, content="v1")
    ctx = GitContext(branch="feature", description="update")

    version = engine.create_version(memory_id=memory.id, content="v2", git_context=ctx)

    assert version.git_context is not None
    assert version.git_context["branch"] == "feature"
    assert version.git_context["description"] == "update"
    assert len(version.evidence) == 2


def test_create_version_without_git_context(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(project_id=project.id, content="v1")

    version = engine.create_version(memory_id=memory.id, content="v2")

    assert version.git_context is None
    assert len(version.evidence) == 0


# --- get_version ---


def test_get_version_returns_version_with_evidence(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(
        project_id=project.id, content="v1", git_context=GitContext(branch="main")
    )

    version = engine.get_version(memory_id=memory.id, sequence=1)

    assert version is not None
    assert version.git_context == {"branch": "main"}
    assert len(version.evidence) == 1


def test_get_version_nonexistent_returns_none(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(project_id=project.id, content="v1")

    version = engine.get_version(memory_id=memory.id, sequence=999)

    assert version is None


def test_get_version_unknown_memory_raises(engine: ChronicleEngine):
    with pytest.raises(MemoryNotFoundError):
        engine.get_version(memory_id="missing", sequence=1)


# --- get_evidence ---


def test_get_evidence_returns_evidence_list(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(
        project_id=project.id,
        content="v1",
        git_context=GitContext(branch="main", commit="abc123"),
    )

    evidence = engine.get_evidence(memory_id=memory.id, sequence=1)

    assert len(evidence) == 2
    types = {e.evidence_type for e in evidence}
    assert types == {"branch", "commit"}


def test_get_evidence_empty_when_no_git_context(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(project_id=project.id, content="v1")

    evidence = engine.get_evidence(memory_id=memory.id, sequence=1)

    assert evidence == []


def test_get_evidence_unknown_memory_raises(engine: ChronicleEngine):
    with pytest.raises(MemoryNotFoundError):
        engine.get_evidence(memory_id="missing", sequence=1)


def test_get_evidence_nonexistent_version_returns_empty(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(project_id=project.id, content="v1")

    evidence = engine.get_evidence(memory_id=memory.id, sequence=999)

    assert evidence == []


# --- Multiple versions with different git contexts ---


def test_different_versions_have_independent_git_contexts(engine: ChronicleEngine):
    project = _make_project(engine)
    memory = engine.create_memory(
        project_id=project.id, content="v1", git_context=GitContext(branch="main")
    )
    v2 = engine.create_version(
        memory_id=memory.id, content="v2", git_context=GitContext(commit="abc")
    )
    v3 = engine.create_version(memory_id=memory.id, content="v3")

    assert v2.git_context == {"commit": "abc"}
    assert v3.git_context is None
    assert engine.get_version(memory.id, 1).git_context == {"branch": "main"}
    assert engine.get_version(memory.id, 2).git_context == {"commit": "abc"}
    assert engine.get_version(memory.id, 3).git_context is None
