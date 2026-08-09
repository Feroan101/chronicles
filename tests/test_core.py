import pytest
from chronicle.core import (
    ChronicleEngine,
    ConfidenceScoreRangeError,
    CrossProjectRelationshipError,
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
