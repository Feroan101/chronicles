import subprocess
from datetime import timedelta
from pathlib import Path

import pytest
from chronicle.core import (
    ChronicleEngine,
    ConfidenceScoreRangeError,
    CrossProjectRelationshipError,
    DecayConfigError,
    InvalidObservationActionError,
    MemoryNotFoundError,
    MemoryVersionNotFoundError,
    ObservationAlreadyProcessedError,
    ObservationNotFoundError,
    ProjectNotFoundError,
    RelationshipNotFoundError,
    SelfRelationshipError,
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
# Observation tests
# ------------------------------------------------------------------


def test_create_observation(engine):
    project = engine.create_project(name="demo")

    observation = engine.create_observation(project_id=project.id, content="discovered something")

    assert observation.project_id == project.id
    assert observation.content == "discovered something"
    assert observation.status == "pending"
    assert observation.processed_at is None


def test_create_observation_unknown_project_raises(engine):
    with pytest.raises(ProjectNotFoundError):
        engine.create_observation(project_id="missing", content="x")


def test_list_observations_returns_ordered(engine):
    project = engine.create_project(name="demo")
    first = engine.create_observation(project_id=project.id, content="a")
    second = engine.create_observation(project_id=project.id, content="b")

    observations = engine.list_observations(project_id=project.id)

    assert [o.id for o in observations] == [first.id, second.id]


def test_list_observations_unknown_project_is_empty(engine):
    assert engine.list_observations(project_id="missing") == []


def test_process_observation_create_memory(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="new knowledge")

    result = engine.process_observation(observation_id=observation.id, action="create_memory")

    assert result.status == "processed"
    assert result.processed_at is not None

    memories = engine.list_memories(project_id=project.id)
    assert len(memories) == 1
    assert memories[0].versions[0].content == "new knowledge"


def test_process_observation_update_memory(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="original")
    observation = engine.create_observation(project_id=project.id, content="updated knowledge")

    result = engine.process_observation(
        observation_id=observation.id, action="update_memory", memory_id=memory.id
    )

    assert result.status == "processed"

    fetched = engine.get_memory(memory.id)
    assert len(fetched.versions) == 2
    assert fetched.versions[1].content == "updated knowledge"


def test_process_observation_update_requires_memory_id(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="x")

    with pytest.raises(MemoryNotFoundError):
        engine.process_observation(observation_id=observation.id, action="update_memory")


def test_process_observation_update_unknown_memory_raises(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="x")

    with pytest.raises(MemoryNotFoundError):
        engine.process_observation(
            observation_id=observation.id, action="update_memory", memory_id="missing"
        )


def test_process_observation_update_cross_project_raises(engine):
    project_a = engine.create_project(name="a")
    project_b = engine.create_project(name="b")
    memory = engine.create_memory(project_id=project_a.id, content="original")
    observation = engine.create_observation(project_id=project_b.id, content="x")

    with pytest.raises(CrossProjectRelationshipError):
        engine.process_observation(
            observation_id=observation.id, action="update_memory", memory_id=memory.id
        )


def test_process_observation_discard(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="not useful")

    result = engine.process_observation(observation_id=observation.id, action="discard")

    assert result.status == "discarded"
    assert result.processed_at is not None
    assert engine.list_memories(project_id=project.id) == []


def test_process_observation_invalid_action_raises(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="x")

    with pytest.raises(InvalidObservationActionError):
        engine.process_observation(observation_id=observation.id, action="invalid")


def test_process_observation_already_processed_raises(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="x")

    engine.process_observation(observation_id=observation.id, action="discard")

    with pytest.raises(ObservationAlreadyProcessedError):
        engine.process_observation(observation_id=observation.id, action="discard")


def test_process_observation_unknown_observation_raises(engine):
    with pytest.raises(ObservationNotFoundError):
        engine.process_observation(observation_id="missing", action="discard")


def test_process_observation_create_memory_registers_on_branch(engine):
    project = engine.create_project(name="demo")
    observation = engine.create_observation(project_id=project.id, content="branch knowledge")

    engine.process_observation(observation_id=observation.id, action="create_memory")

    branch = engine.get_current_branch(project.id)
    knowledge = engine.get_branch_knowledge(branch.id)
    assert len(knowledge) == 1
    assert knowledge[0].version.content == "branch knowledge"
    appearances = engine.list_memories(project_id=project.id, branch_id=branch.id)
    assert len(appearances) == 1


def test_process_observation_update_memory_registers_on_branch(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="original")
    observation = engine.create_observation(project_id=project.id, content="updated on branch")

    engine.process_observation(
        observation_id=observation.id, action="update_memory", memory_id=memory.id
    )

    branch = engine.get_current_branch(project.id)
    knowledge = engine.get_branch_knowledge(branch.id)
    assert len(knowledge) == 1
    assert knowledge[0].version.content == "updated on branch"


# ------------------------------------------------------------------
# Relationship tests
# ------------------------------------------------------------------


def test_create_relationship(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")

    rel = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="caused_by",
    )

    assert rel.project_id == project.id
    assert rel.from_memory_id == mem_a.id
    assert rel.to_memory_id == mem_b.id
    assert rel.type == "caused_by"


def test_create_relationship_self_raises(engine):
    project = engine.create_project(name="demo")
    mem = engine.create_memory(project_id=project.id, content="a")

    with pytest.raises(SelfRelationshipError):
        engine.create_relationship(
            project_id=project.id,
            from_memory_id=mem.id,
            to_memory_id=mem.id,
            type="related_to",
        )


def test_create_relationship_unknown_project_raises(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")

    with pytest.raises(ProjectNotFoundError):
        engine.create_relationship(
            project_id="missing",
            from_memory_id=mem_a.id,
            to_memory_id=mem_b.id,
            type="related_to",
        )


def test_create_relationship_unknown_from_memory_raises(engine):
    project = engine.create_project(name="demo")
    mem_b = engine.create_memory(project_id=project.id, content="b")

    with pytest.raises(MemoryNotFoundError):
        engine.create_relationship(
            project_id=project.id,
            from_memory_id="missing",
            to_memory_id=mem_b.id,
            type="related_to",
        )


def test_create_relationship_unknown_to_memory_raises(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")

    with pytest.raises(MemoryNotFoundError):
        engine.create_relationship(
            project_id=project.id,
            from_memory_id=mem_a.id,
            to_memory_id="missing",
            type="related_to",
        )


def test_create_relationship_cross_project_raises(engine):
    project_a = engine.create_project(name="a")
    project_b = engine.create_project(name="b")
    mem_a = engine.create_memory(project_id=project_a.id, content="a")
    mem_b = engine.create_memory(project_id=project_b.id, content="b")

    with pytest.raises(CrossProjectRelationshipError):
        engine.create_relationship(
            project_id=project_a.id,
            from_memory_id=mem_a.id,
            to_memory_id=mem_b.id,
            type="related_to",
        )


def test_list_relationships_returns_ordered(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")
    mem_c = engine.create_memory(project_id=project.id, content="c")
    first = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="caused_by",
    )
    second = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_b.id,
        to_memory_id=mem_c.id,
        type="resolved_by",
    )

    relationships = engine.list_relationships(project_id=project.id)

    assert [r.id for r in relationships] == [first.id, second.id]


def test_list_relationships_unknown_project_is_empty(engine):
    assert engine.list_relationships(project_id="missing") == []


def test_get_relationships_for_memory(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")
    mem_c = engine.create_memory(project_id=project.id, content="c")
    rel_ab = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="caused_by",
    )
    rel_bc = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_b.id,
        to_memory_id=mem_c.id,
        type="resolved_by",
    )

    rels = engine.get_relationships_for_memory(memory_id=mem_b.id)

    assert len(rels) == 2
    rel_ids = {r.id for r in rels}
    assert rel_ab.id in rel_ids
    assert rel_bc.id in rel_ids


def test_get_relationships_for_memory_no_matches(engine):
    project = engine.create_project(name="demo")
    mem = engine.create_memory(project_id=project.id, content="isolated")

    rels = engine.get_relationships_for_memory(memory_id=mem.id)

    assert rels == []


def test_remove_relationship(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")
    rel = engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="related_to",
    )

    engine.remove_relationship(relationship_id=rel.id)

    assert engine.list_relationships(project_id=project.id) == []


def test_remove_relationship_unknown_raises(engine):
    with pytest.raises(RelationshipNotFoundError):
        engine.remove_relationship(relationship_id="missing")


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


# ------------------------------------------------------------------
# Confidence tests
# ------------------------------------------------------------------


def test_record_confidence(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    record = engine.record_confidence(
        memory_id=memory.id, sequence=1, score=0.8, reason="well supported"
    )

    assert record.score == 0.8
    assert record.reason == "well supported"
    assert record.memory_version_id == memory.versions[0].id


def test_record_confidence_unknown_memory_raises(engine):
    with pytest.raises(MemoryNotFoundError):
        engine.record_confidence(memory_id="missing", sequence=1, score=0.5)


def test_record_confidence_unknown_version_raises(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    with pytest.raises(MemoryVersionNotFoundError):
        engine.record_confidence(memory_id=memory.id, sequence=99, score=0.5)


def test_record_confidence_out_of_range_raises(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    with pytest.raises(ConfidenceScoreRangeError):
        engine.record_confidence(memory_id=memory.id, sequence=1, score=1.5)

    with pytest.raises(ConfidenceScoreRangeError):
        engine.record_confidence(memory_id=memory.id, sequence=1, score=-0.1)


def test_record_confidence_boundary_values(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    low = engine.record_confidence(memory_id=memory.id, sequence=1, score=0.0)
    assert low.score == 0.0

    high = engine.record_confidence(memory_id=memory.id, sequence=1, score=1.0)
    assert high.score == 1.0


def test_get_confidence_returns_latest(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.5)
    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.9)

    current = engine.get_confidence(memory_id=memory.id, sequence=1)
    assert current is not None
    assert current.score == 0.9


def test_get_confidence_no_records_returns_none(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    assert engine.get_confidence(memory_id=memory.id, sequence=1) is None


def test_get_confidence_unknown_memory_raises(engine):
    with pytest.raises(MemoryNotFoundError):
        engine.get_confidence(memory_id="missing", sequence=1)


def test_get_confidence_history_returns_all(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.3, reason="initial")
    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.7, reason="updated")
    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.9, reason="final")

    history = engine.get_confidence_history(memory_id=memory.id, sequence=1)
    assert len(history) == 3
    assert [s.score for s in history] == [0.3, 0.7, 0.9]
    assert [s.reason for s in history] == ["initial", "updated", "final"]


def test_get_confidence_history_empty(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    history = engine.get_confidence_history(memory_id=memory.id, sequence=1)
    assert history == []


def test_get_confidence_history_unknown_memory_raises(engine):
    with pytest.raises(MemoryNotFoundError):
        engine.get_confidence_history(memory_id="missing", sequence=1)


def test_confidence_without_reason(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    record = engine.record_confidence(memory_id=memory.id, sequence=1, score=0.6)
    assert record.reason is None


# ------------------------------------------------------------------
# Verification tests
# ------------------------------------------------------------------


def test_verify_project_passes(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge", type="fact")

    report = engine.verify_project(project_id=project.id)

    assert report.scope == "project"
    assert report.scope_id == project.id
    assert report.passed
    assert not report.has_failures
    assert len(report.results) > 0
    assert all(r.outcome == "verified" for r in report.results)


def test_verify_project_unknown_project_raises(engine):
    from chronicle.core import ProjectNotFoundError

    with pytest.raises(ProjectNotFoundError):
        engine.verify_project(project_id="missing")


def test_verify_project_with_relationships(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a", type="fact")
    mem_b = engine.create_memory(project_id=project.id, content="b", type="fact")
    engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="caused_by",
    )

    report = engine.verify_project(project_id=project.id)

    assert report.passed
    rel_checks = [r for r in report.results if r.check == "relationship_consistency"]
    assert len(rel_checks) == 1
    assert rel_checks[0].outcome == "verified"


def test_verify_project_inconclusive_without_evidence(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.verify_project(project_id=project.id)

    trace_checks = [r for r in report.results if r.check == "traceability"]
    assert len(trace_checks) == 1
    assert trace_checks[0].outcome == "inconclusive"


def test_verify_project_traceable_with_type(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge", type="fact")

    report = engine.verify_project(project_id=project.id)

    trace_checks = [r for r in report.results if r.check == "traceability"]
    assert len(trace_checks) == 1
    assert trace_checks[0].outcome == "verified"


def test_verify_project_traceable_with_context(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge", context="always")

    report = engine.verify_project(project_id=project.id)

    trace_checks = [r for r in report.results if r.check == "traceability"]
    assert trace_checks[0].outcome == "verified"


def test_verify_project_traceable_with_evidence(engine):
    from chronicle.models import Evidence
    from chronicle.storage import EvidenceRepository
    from chronicle.utils.ids import new_uuid
    from chronicle.utils.time import utcnow

    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    with engine._transaction() as session:
        EvidenceRepository(session).create(
            Evidence(
                id=new_uuid(),
                memory_version_id=memory.versions[0].id,
                evidence_type="commit",
                ref="abc123",
                recorded_at=utcnow(),
            )
        )

    report = engine.verify_project(project_id=project.id)

    trace_checks = [r for r in report.results if r.check == "traceability"]
    assert trace_checks[0].outcome == "verified"


def test_verify_memory_passes(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge", type="fact")

    report = engine.verify_memory(memory_id=memory.id)

    assert report.scope == "memory"
    assert report.scope_id == memory.id
    assert report.passed


def test_verify_memory_unknown_raises(engine):
    from chronicle.core import MemoryNotFoundError

    with pytest.raises(MemoryNotFoundError):
        engine.verify_memory(memory_id="missing")


def test_verify_memory_version_integrity(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1", type="fact")
    engine.create_version(memory_id=memory.id, content="v2")

    report = engine.verify_memory(memory_id=memory.id)

    seq_checks = [r for r in report.results if r.check == "version_sequence_order"]
    assert len(seq_checks) == 1
    assert seq_checks[0].outcome == "verified"


def test_verify_version_passes(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge", context="ctx")

    report = engine.verify_version(memory_id=memory.id, sequence=1)

    assert report.scope == "version"
    assert report.scope_id == f"{memory.id}:1"
    assert report.passed
    assert not report.has_failures
    checks = {r.check: r.outcome for r in report.results}
    assert checks["version_sequence_order"] == "verified"
    assert checks["traceability"] == "verified"


def test_verify_version_unknown_memory_raises(engine):
    from chronicle.core import MemoryNotFoundError

    with pytest.raises(MemoryNotFoundError):
        engine.verify_version(memory_id="missing", sequence=1)


def test_verify_version_unknown_sequence_raises(engine):
    from chronicle.core import MemoryVersionNotFoundError

    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    with pytest.raises(MemoryVersionNotFoundError):
        engine.verify_version(memory_id=memory.id, sequence=99)


def test_verify_version_inconclusive_without_evidence(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.verify_version(memory_id=memory.id, sequence=1)

    trace_checks = [r for r in report.results if r.check == "traceability"]
    assert len(trace_checks) == 1
    assert trace_checks[0].outcome == "inconclusive"
    assert "origin cannot be established" in trace_checks[0].message


def test_verify_version_traceable_with_evidence(engine):
    from chronicle.models import Evidence
    from chronicle.storage import EvidenceRepository
    from chronicle.utils.ids import new_uuid
    from chronicle.utils.time import utcnow

    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    with engine._transaction() as session:
        EvidenceRepository(session).create(
            Evidence(
                id=new_uuid(),
                memory_version_id=memory.versions[0].id,
                evidence_type="commit",
                ref="abc123",
                recorded_at=utcnow(),
            )
        )

    report = engine.verify_version(memory_id=memory.id, sequence=1)

    trace_checks = [r for r in report.results if r.check == "traceability"]
    assert trace_checks[0].outcome == "verified"


def test_verify_version_does_not_modify_knowledge(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge", context="ctx")

    engine.verify_version(memory_id=memory.id, sequence=1)

    fetched = engine.get_memory(memory.id)
    assert len(fetched.versions) == 1
    assert fetched.versions[0].content == "knowledge"
    assert fetched.versions[0].context == "ctx"


def test_verify_snapshot_passes(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge")
    snapshot = engine.create_snapshot(project_id=project.id)

    report = engine.verify_snapshot(snapshot_id=snapshot.id)

    assert report.scope == "snapshot"
    assert report.scope_id == snapshot.id
    assert report.passed
    member_checks = [r for r in report.results if r.check == "snapshot_member_version_exists"]
    assert len(member_checks) == 1
    assert member_checks[0].outcome == "verified"


def test_verify_snapshot_unknown_raises(engine):
    from chronicle.core import SnapshotNotFoundError

    with pytest.raises(SnapshotNotFoundError):
        engine.verify_snapshot(snapshot_id="missing")


def test_verify_snapshot_with_relationships(engine):
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")
    engine.create_relationship(
        project_id=project.id,
        from_memory_id=mem_a.id,
        to_memory_id=mem_b.id,
        type="caused_by",
    )
    snapshot = engine.create_snapshot(project_id=project.id)

    report = engine.verify_snapshot(snapshot_id=snapshot.id)

    rel_checks = [r for r in report.results if r.check == "snapshot_relationship_exists"]
    assert len(rel_checks) == 1
    assert rel_checks[0].outcome == "verified"


def test_verify_snapshot_empty(engine):
    project = engine.create_project(name="empty")
    snapshot = engine.create_snapshot(project_id=project.id)

    report = engine.verify_snapshot(snapshot_id=snapshot.id)

    assert report.passed
    assert len(report.results) == 0


def test_verification_does_not_modify_knowledge(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge", type="fact")

    engine.verify_project(project_id=project.id)

    fetched = engine.get_memory(memory.id)
    assert fetched.type == "fact"
    assert len(fetched.versions) == 1
    assert fetched.versions[0].content == "knowledge"


def test_verification_does_not_modify_confidence(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.8)

    engine.verify_project(project_id=project.id)

    confidence = engine.get_confidence(memory_id=memory.id, sequence=1)
    assert confidence is not None
    assert confidence.score == 0.8


# ------------------------------------------------------------------
# Drift detection tests
# ------------------------------------------------------------------


def _git(repo: Path, *args: str):
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )


def _init_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Chronicle Test")
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src" / "main.py").write_text("print('hi')\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _branch(repo: Path) -> str:
    return _git(repo, "branch", "--show-current").stdout.strip()


def _add_evidence(engine, memory, evidence_type: str, ref: str) -> None:
    from chronicle.models import Evidence
    from chronicle.storage import EvidenceRepository
    from chronicle.utils.ids import new_uuid
    from chronicle.utils.time import utcnow

    with engine._transaction() as session:
        EvidenceRepository(session).create(
            Evidence(
                id=new_uuid(),
                memory_version_id=memory.versions[0].id,
                evidence_type=evidence_type,
                ref=ref,
                recorded_at=utcnow(),
            )
        )


def test_detect_drift_clean(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        git_context=GitContext(commit=_head(repo), branch=_branch(repo)),
    )

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.project_id == project.id
    assert report.clean
    assert report.state == "clean"
    assert report.changed_artifacts == []
    assert report.affected_knowledge == []


def test_detect_drift_abbreviated_commit_matches(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        git_context=GitContext(commit=_head(repo)[:7]),
    )

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.clean
    assert report.affected_knowledge == []


def test_detect_drift_dirty_unrelated_changes(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        git_context=GitContext(commit=_head(repo)),
    )

    (repo / "README.md").write_text("readme")

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.dirty
    assert report.changed_artifacts == ["README.md"]
    assert report.affected_knowledge == []


def test_detect_drift_dirty_evidence_relevant(engine, tmp_path):
    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="uses main module")
    _add_evidence(engine, memory, "file", "src/main.py")

    (repo / "src" / "main.py").write_text("print('bye')\n")

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.dirty
    assert "src/main.py" in report.changed_artifacts
    assert len(report.affected_knowledge) == 1
    knowledge = report.affected_knowledge[0]
    assert knowledge.memory_id == memory.id
    assert knowledge.sequence == 1
    assert knowledge.content == "uses main module"
    assert "src/main.py" in knowledge.reason


def test_detect_drift_multiple_affected(engine, tmp_path):
    repo = _init_repo(tmp_path / "repo")
    (repo / "src" / "util.py").write_text("def helper():\n    pass\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add util")
    project = engine.create_project(name="demo")
    mem_a = engine.create_memory(project_id=project.id, content="a")
    mem_b = engine.create_memory(project_id=project.id, content="b")
    _add_evidence(engine, mem_a, "file", "src/main.py")
    _add_evidence(engine, mem_b, "file", "src/util.py")

    (repo / "src" / "main.py").write_text("print('changed a')\n")
    (repo / "src" / "util.py").write_text("def helper():\n    return 1\n")

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.dirty
    assert len(report.affected_knowledge) == 2
    affected_ids = {k.memory_id for k in report.affected_knowledge}
    assert affected_ids == {mem_a.id, mem_b.id}


def test_detect_drift_commit_mismatch_affected(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        git_context=GitContext(commit="deadbeef"),
    )

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.dirty
    assert report.changed_artifacts == []
    assert len(report.affected_knowledge) == 1
    assert "recorded commit" in report.affected_knowledge[0].reason


def test_detect_drift_branch_mismatch_affected(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        git_context=GitContext(branch="feature"),
    )

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.dirty
    assert len(report.affected_knowledge) == 1
    assert "recorded branch" in report.affected_knowledge[0].reason


def test_detect_drift_no_git_context(engine, tmp_path):
    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert report.clean
    assert report.changed_artifacts == []
    assert report.affected_knowledge == []
    assert any("no Git context" in reason for reason in report.reasons)


def test_detect_drift_not_a_repo(engine, tmp_path):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.detect_drift(project_id=project.id, repo_path=tmp_path / "empty")

    assert report.clean
    assert any("not in a Git repository" in reason for reason in report.reasons)


def test_detect_drift_unknown_project_raises(engine):
    with pytest.raises(ProjectNotFoundError):
        engine.detect_drift(project_id="missing")


def test_detect_drift_read_only(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    memory = engine.create_memory(
        project_id=project.id,
        content="knowledge",
        type="fact",
        git_context=GitContext(commit=_head(repo)),
    )
    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.8)

    (repo / "README.md").write_text("readme")
    engine.detect_drift(project_id=project.id, repo_path=repo)

    fetched = engine.get_memory(memory.id)
    assert fetched.type == "fact"
    assert len(fetched.versions) == 1
    assert fetched.versions[0].content == "knowledge"
    confidence = engine.get_confidence(memory_id=memory.id, sequence=1)
    assert confidence is not None
    assert confidence.score == 0.8


def test_detect_drift_does_not_affect_verification(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        type="fact",
        git_context=GitContext(commit=_head(repo)),
    )

    before = engine.verify_project(project_id=project.id)
    engine.detect_drift(project_id=project.id, repo_path=repo)
    after = engine.verify_project(project_id=project.id)

    assert after.passed == before.passed
    assert [r.outcome for r in after.results] == [r.outcome for r in before.results]


# ------------------------------------------------------------------
# Memory decay tests
# ------------------------------------------------------------------


def test_assess_decay_fresh(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.assess_decay(project_id=project.id, at=memory.versions[0].created_at)

    assert report.project_id == project.id
    assert report.generated_at is not None
    assert report.fresh_days == 30
    assert report.stale_days == 180
    assert len(report.assessments) == 1
    assessment = report.assessments[0]
    assert assessment.memory_id == memory.id
    assert assessment.sequence == 1
    assert assessment.content == "knowledge"
    assert assessment.fresh
    assert not assessment.aging
    assert not assessment.stale
    assert assessment.state == "fresh"
    assert assessment.freshness == 1.0
    assert assessment.age_days == 0.0
    assert report.stale_count == 0


def test_assess_decay_aging(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.assess_decay(
        project_id=project.id,
        at=memory.versions[0].created_at + timedelta(days=60),
    )

    assessment = report.assessments[0]
    assert assessment.state == "aging"
    assert assessment.aging
    assert not assessment.fresh
    assert not assessment.stale


def test_assess_decay_stale(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.assess_decay(
        project_id=project.id,
        at=memory.versions[0].created_at + timedelta(days=200),
    )

    assessment = report.assessments[0]
    assert assessment.state == "stale"
    assert assessment.stale
    assert assessment.freshness == 0.0
    assert report.stale_count == 1


def test_assess_decay_freshness_is_linear(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")

    report = engine.assess_decay(
        project_id=project.id,
        at=memory.versions[0].created_at + timedelta(days=90),
    )

    assert report.assessments[0].freshness == pytest.approx(0.5)
    assert report.assessments[0].age_days == pytest.approx(90.0)


def test_assess_decay_fresh_boundary(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    created = memory.versions[0].created_at

    just_under = engine.assess_decay(
        project_id=project.id, at=created + timedelta(days=29, seconds=86399)
    )
    assert just_under.assessments[0].fresh

    at_threshold = engine.assess_decay(project_id=project.id, at=created + timedelta(days=30))
    assert at_threshold.assessments[0].aging


def test_assess_decay_stale_boundary(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    created = memory.versions[0].created_at

    just_under = engine.assess_decay(
        project_id=project.id, at=created + timedelta(days=179, seconds=86399)
    )
    assert just_under.assessments[0].aging

    at_threshold = engine.assess_decay(project_id=project.id, at=created + timedelta(days=180))
    assert at_threshold.assessments[0].stale
    assert at_threshold.assessments[0].freshness == 0.0


def test_assess_decay_all_states_across_time(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    created = memory.versions[0].created_at

    fresh = engine.assess_decay(project_id=project.id, at=created + timedelta(days=10))
    aging = engine.assess_decay(project_id=project.id, at=created + timedelta(days=60))
    stale = engine.assess_decay(project_id=project.id, at=created + timedelta(days=300))

    assert fresh.assessments[0].state == "fresh"
    assert aging.assessments[0].state == "aging"
    assert stale.assessments[0].state == "stale"


def test_assess_decay_assesses_current_version_only(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="v1")
    version2 = engine.create_version(memory_id=memory.id, content="v2")

    report = engine.assess_decay(project_id=project.id)

    assert len(report.assessments) == 1
    assessment = report.assessments[0]
    assert assessment.sequence == 2
    assert assessment.content == "v2"
    assert assessment.created_at == version2.created_at


def test_assess_decay_multiple_memories(engine):
    from chronicle.models import MemoryVersion
    from chronicle.utils.time import utcnow
    from sqlalchemy import update

    project = engine.create_project(name="demo")
    fresh_memory = engine.create_memory(project_id=project.id, content="fresh")
    old_memory = engine.create_memory(project_id=project.id, content="old")

    with engine._transaction() as session:
        session.execute(
            update(MemoryVersion)
            .where(MemoryVersion.memory_id == old_memory.id)
            .values(created_at=utcnow() - timedelta(days=200))
        )

    report = engine.assess_decay(project_id=project.id)

    states = {a.memory_id: a.state for a in report.assessments}
    assert states[fresh_memory.id] == "fresh"
    assert states[old_memory.id] == "stale"


def test_assess_decay_empty_project(engine):
    project = engine.create_project(name="empty")

    report = engine.assess_decay(project_id=project.id)

    assert report.assessments == []
    assert report.stale_count == 0


def test_assess_decay_reference_before_creation_is_fresh(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    created = memory.versions[0].created_at

    report = engine.assess_decay(project_id=project.id, at=created - timedelta(days=10))

    assessment = report.assessments[0]
    assert assessment.fresh
    assert assessment.freshness == 1.0
    assert assessment.age_days == 0.0


def test_assess_decay_accepts_timezone_aware_reference(engine):
    from datetime import UTC, datetime

    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    created = memory.versions[0].created_at
    aware = datetime.combine(created.date(), created.time(), tzinfo=UTC) + timedelta(days=60)

    report = engine.assess_decay(project_id=project.id, at=aware)

    assert report.assessments[0].aging


def test_assess_decay_deterministic(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(project_id=project.id, content="knowledge")
    at = memory.versions[0].created_at + timedelta(days=90)

    first = engine.assess_decay(project_id=project.id, at=at)
    second = engine.assess_decay(project_id=project.id, at=at)

    assert first == second


def test_assess_decay_unknown_project_raises(engine):
    with pytest.raises(ProjectNotFoundError):
        engine.assess_decay(project_id="missing")


def test_assess_decay_invalid_config_raises(engine):
    project = engine.create_project(name="demo")

    with pytest.raises(DecayConfigError):
        engine.assess_decay(project_id=project.id, fresh_days=0)

    with pytest.raises(DecayConfigError):
        engine.assess_decay(project_id=project.id, stale_days=-1)

    with pytest.raises(DecayConfigError):
        engine.assess_decay(project_id=project.id, fresh_days=100, stale_days=50)


def test_assess_decay_read_only(engine):
    project = engine.create_project(name="demo")
    memory = engine.create_memory(
        project_id=project.id, content="knowledge", type="fact", context="ctx"
    )
    engine.record_confidence(memory_id=memory.id, sequence=1, score=0.8)

    engine.assess_decay(project_id=project.id)

    fetched = engine.get_memory(memory.id)
    assert fetched.type == "fact"
    assert len(fetched.versions) == 1
    assert fetched.versions[0].content == "knowledge"
    assert fetched.versions[0].context == "ctx"
    confidence = engine.get_confidence(memory_id=memory.id, sequence=1)
    assert confidence is not None
    assert confidence.score == 0.8


def test_assess_decay_does_not_affect_verification(engine):
    project = engine.create_project(name="demo")
    engine.create_memory(project_id=project.id, content="knowledge", type="fact")

    before = engine.verify_project(project_id=project.id)
    engine.assess_decay(project_id=project.id)
    after = engine.verify_project(project_id=project.id)

    assert after.passed == before.passed
    assert [r.outcome for r in after.results] == [r.outcome for r in before.results]


def test_assess_decay_does_not_affect_drift(engine, tmp_path):
    from chronicle.core import GitContext

    repo = _init_repo(tmp_path / "repo")
    project = engine.create_project(name="demo")
    engine.create_memory(
        project_id=project.id,
        content="knowledge",
        git_context=GitContext(commit=_head(repo), branch=_branch(repo)),
    )

    before = engine.detect_drift(project_id=project.id, repo_path=repo)
    engine.assess_decay(project_id=project.id)
    after = engine.detect_drift(project_id=project.id, repo_path=repo)

    assert after.state == before.state
    assert after.changed_artifacts == before.changed_artifacts
    assert [k.reason for k in after.affected_knowledge] == [
        k.reason for k in before.affected_knowledge
    ]
