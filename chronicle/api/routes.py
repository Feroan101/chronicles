from fastapi import APIRouter, Query

from chronicle.api.deps import Engine
from chronicle.api.schemas import (
    BranchCreate,
    BranchKnowledgeRead,
    BranchRead,
    BranchSwitch,
    ConfidenceRead,
    ConfidenceRecord,
    DecayAssessmentRead,
    DecayReportRead,
    DriftAffectedKnowledgeRead,
    DriftReportRead,
    EvidenceRead,
    MemoryCreate,
    MemoryRead,
    MemorySummaryRead,
    MemoryUpdate,
    MemoryVersionRead,
    ObservationCreate,
    ObservationProcess,
    ObservationRead,
    ProjectCreate,
    ProjectRead,
    RelationshipCreate,
    RelationshipRead,
    SearchHitRead,
    SnapshotCreate,
    SnapshotRead,
    VerificationReportRead,
    VerificationResultRead,
    VersionCreate,
)
from chronicle.core import (
    BranchNotFoundError,
    ChronicleEngine,
    GitContext,
    GitContextError,
    MemoryNotFoundError,
    ProjectNotFoundError,
    SnapshotNotFoundError,
)

router = APIRouter()


def _memory_read(engine: ChronicleEngine, memory_id: str) -> MemoryRead:
    memory = engine.get_memory(memory_id)
    if memory is None:
        raise MemoryNotFoundError(memory_id)
    return MemoryRead.model_validate(memory)


def _build_git_context(payload_git_context) -> GitContext | None:
    if payload_git_context is None:
        return None
    try:
        return GitContext(
            branch=payload_git_context.branch,
            commit=payload_git_context.commit,
            description=payload_git_context.description,
        )
    except GitContextError as exc:
        raise GitContextError(str(exc)) from exc


@router.post("/projects", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, engine: Engine) -> ProjectRead:
    return ProjectRead.model_validate(
        engine.create_project(name=payload.name, description=payload.description)
    )


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, engine: Engine) -> ProjectRead:
    project = engine.get_project(project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)
    return ProjectRead.model_validate(project)


# ------------------------------------------------------------------
# Branch endpoints
# ------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/branches", response_model=BranchRead, status_code=201
)
def create_branch(project_id: str, payload: BranchCreate, engine: Engine) -> BranchRead:
    return BranchRead.model_validate(
        engine.create_branch(
            project_id=project_id,
            name=payload.name,
            source_branch_id=payload.source_branch_id,
        )
    )


@router.get("/projects/{project_id}/branches", response_model=list[BranchRead])
def list_branches(project_id: str, engine: Engine) -> list[BranchRead]:
    return [BranchRead.model_validate(b) for b in engine.list_branches(project_id)]


@router.get("/branches/{branch_id}", response_model=BranchRead)
def get_branch(branch_id: str, engine: Engine) -> BranchRead:
    branch = engine.get_branch(branch_id)
    if branch is None:
        raise BranchNotFoundError(branch_id)
    return BranchRead.model_validate(branch)


@router.get(
    "/projects/{project_id}/branches/current", response_model=BranchRead
)
def get_current_branch(project_id: str, engine: Engine) -> BranchRead:
    return BranchRead.model_validate(engine.get_current_branch(project_id))


@router.post(
    "/projects/{project_id}/branches/current", response_model=BranchRead
)
def switch_branch(project_id: str, payload: BranchSwitch, engine: Engine) -> BranchRead:
    return BranchRead.model_validate(engine.switch_branch(project_id, payload.name))


@router.get("/branches/{branch_id}/knowledge", response_model=list[BranchKnowledgeRead])
def get_branch_knowledge(branch_id: str, engine: Engine) -> list[BranchKnowledgeRead]:
    return [
        BranchKnowledgeRead(
            memory=MemorySummaryRead.model_validate(item.memory),
            version=MemoryVersionRead.model_validate(item.version),
        )
        for item in engine.get_branch_knowledge(branch_id)
    ]


@router.post("/memories", response_model=MemoryRead, status_code=201)
def create_memory(payload: MemoryCreate, engine: Engine) -> MemoryRead:
    return MemoryRead.model_validate(
        engine.create_memory(
            project_id=payload.project_id,
            content=payload.content,
            type=payload.type,
            context=payload.context,
            git_context=_build_git_context(payload.git_context),
        )
    )


@router.get("/memories/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: str, engine: Engine) -> MemoryRead:
    return _memory_read(engine, memory_id)


@router.get("/projects/{project_id}/memories", response_model=list[MemoryRead])
def list_memories(
    project_id: str,
    engine: Engine,
    branch_id: str | None = Query(default=None),
) -> list[MemoryRead]:
    memories = engine.list_memories(project_id, branch_id=branch_id)
    return [MemoryRead.model_validate(memory) for memory in memories]


@router.patch("/memories/{memory_id}", response_model=MemoryRead)
def update_memory(memory_id: str, payload: MemoryUpdate, engine: Engine) -> MemoryRead:
    if "type" in payload.model_fields_set:
        return MemoryRead.model_validate(
            engine.update_memory(memory_id=memory_id, type=payload.type)
        )
    return _memory_read(engine, memory_id)


@router.post("/memories/{memory_id}/versions", response_model=MemoryVersionRead, status_code=201)
def create_version(memory_id: str, payload: VersionCreate, engine: Engine) -> MemoryVersionRead:
    return MemoryVersionRead.model_validate(
        engine.create_version(
            memory_id=memory_id,
            content=payload.content,
            context=payload.context,
            git_context=_build_git_context(payload.git_context),
        )
    )


@router.get("/memories/{memory_id}/versions/{sequence}/evidence", response_model=list[EvidenceRead])
def get_evidence(memory_id: str, sequence: int, engine: Engine) -> list[EvidenceRead]:
    evidence = engine.get_evidence(memory_id=memory_id, sequence=sequence)
    return [EvidenceRead.model_validate(e) for e in evidence]


@router.get("/search", response_model=list[SearchHitRead])
def search(
    query: str,
    engine: Engine,
    project_id: str | None = Query(default=None),
    branch_id: str | None = Query(default=None),
) -> list[SearchHitRead]:
    results = engine.search(query=query, project_id=project_id, branch_id=branch_id)
    return [
        SearchHitRead(
            memory=MemorySummaryRead.model_validate(result.memory),
            version=MemoryVersionRead.model_validate(result.version),
            rank=result.rank,
        )
        for result in results
    ]


# ------------------------------------------------------------------
# Observation endpoints
# ------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/observations",
    response_model=ObservationRead,
    status_code=201,
)
def create_observation(
    project_id: str, payload: ObservationCreate, engine: Engine
) -> ObservationRead:
    return ObservationRead.model_validate(
        engine.create_observation(project_id=project_id, content=payload.content)
    )


@router.get("/projects/{project_id}/observations", response_model=list[ObservationRead])
def list_observations(project_id: str, engine: Engine) -> list[ObservationRead]:
    return [ObservationRead.model_validate(obs) for obs in engine.list_observations(project_id)]


@router.post(
    "/observations/{observation_id}/process",
    response_model=ObservationRead,
)
def process_observation(
    observation_id: str, payload: ObservationProcess, engine: Engine
) -> ObservationRead:
    return ObservationRead.model_validate(
        engine.process_observation(
            observation_id=observation_id,
            action=payload.action,
            memory_id=payload.memory_id,
        )
    )


# ------------------------------------------------------------------
# Relationship endpoints
# ------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/relationships",
    response_model=RelationshipRead,
    status_code=201,
)
def create_relationship(
    project_id: str, payload: RelationshipCreate, engine: Engine
) -> RelationshipRead:
    return RelationshipRead.model_validate(
        engine.create_relationship(
            project_id=project_id,
            from_memory_id=payload.from_memory_id,
            to_memory_id=payload.to_memory_id,
            type=payload.type,
        )
    )


@router.get("/projects/{project_id}/relationships", response_model=list[RelationshipRead])
def list_relationships(project_id: str, engine: Engine) -> list[RelationshipRead]:
    return [RelationshipRead.model_validate(rel) for rel in engine.list_relationships(project_id)]


@router.get("/memories/{memory_id}/relationships", response_model=list[RelationshipRead])
def get_relationships_for_memory(memory_id: str, engine: Engine) -> list[RelationshipRead]:
    return [
        RelationshipRead.model_validate(rel)
        for rel in engine.get_relationships_for_memory(memory_id)
    ]


@router.delete("/relationships/{relationship_id}", status_code=204)
def remove_relationship(relationship_id: str, engine: Engine) -> None:
    engine.remove_relationship(relationship_id)


# ------------------------------------------------------------------
# Snapshot endpoints
# ------------------------------------------------------------------


@router.post("/projects/{project_id}/snapshots", response_model=SnapshotRead, status_code=201)
def create_snapshot(project_id: str, payload: SnapshotCreate, engine: Engine) -> SnapshotRead:
    return SnapshotRead.model_validate(
        engine.create_snapshot(
            project_id=project_id,
            message=payload.message,
            branch_id=payload.branch_id,
        )
    )


@router.get("/projects/{project_id}/snapshots", response_model=list[SnapshotRead])
def list_snapshots(
    project_id: str,
    engine: Engine,
    branch_id: str | None = Query(default=None),
) -> list[SnapshotRead]:
    return [
        SnapshotRead.model_validate(snapshot)
        for snapshot in engine.list_snapshots(project_id, branch_id=branch_id)
    ]


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotRead)
def get_snapshot(snapshot_id: str, engine: Engine) -> SnapshotRead:
    snapshot = engine.get_snapshot(snapshot_id)
    if snapshot is None:
        raise SnapshotNotFoundError(snapshot_id)
    return SnapshotRead.model_validate(snapshot)


# ------------------------------------------------------------------
# Confidence endpoints
# ------------------------------------------------------------------


@router.post(
    "/memories/{memory_id}/versions/{sequence}/confidence",
    response_model=ConfidenceRead,
    status_code=201,
)
def record_confidence(
    memory_id: str, sequence: int, payload: ConfidenceRecord, engine: Engine
) -> ConfidenceRead:
    return ConfidenceRead.model_validate(
        engine.record_confidence(
            memory_id=memory_id,
            sequence=sequence,
            score=payload.score,
            reason=payload.reason,
        )
    )


@router.get(
    "/memories/{memory_id}/versions/{sequence}/confidence",
    response_model=ConfidenceRead | None,
)
def get_confidence(memory_id: str, sequence: int, engine: Engine) -> ConfidenceRead | None:
    score = engine.get_confidence(memory_id=memory_id, sequence=sequence)
    if score is None:
        return None
    return ConfidenceRead.model_validate(score)


@router.get(
    "/memories/{memory_id}/versions/{sequence}/confidence/history",
    response_model=list[ConfidenceRead],
)
def get_confidence_history(memory_id: str, sequence: int, engine: Engine) -> list[ConfidenceRead]:
    history = engine.get_confidence_history(memory_id=memory_id, sequence=sequence)
    return [ConfidenceRead.model_validate(s) for s in history]


# ------------------------------------------------------------------
# Verification endpoints
# ------------------------------------------------------------------


def _verification_report(report) -> VerificationReportRead:
    return VerificationReportRead(
        scope=report.scope,
        scope_id=report.scope_id,
        results=[
            VerificationResultRead(check=r.check, outcome=r.outcome, message=r.message)
            for r in report.results
        ],
        passed=report.passed,
        has_failures=report.has_failures,
    )


@router.post(
    "/projects/{project_id}/verify",
    response_model=VerificationReportRead,
)
def verify_project(project_id: str, engine: Engine) -> VerificationReportRead:
    return _verification_report(engine.verify_project(project_id=project_id))


@router.post(
    "/memories/{memory_id}/verify",
    response_model=VerificationReportRead,
)
def verify_memory(memory_id: str, engine: Engine) -> VerificationReportRead:
    return _verification_report(engine.verify_memory(memory_id=memory_id))


@router.post(
    "/memories/{memory_id}/versions/{sequence}/verify",
    response_model=VerificationReportRead,
)
def verify_version(memory_id: str, sequence: int, engine: Engine) -> VerificationReportRead:
    return _verification_report(engine.verify_version(memory_id=memory_id, sequence=sequence))


@router.post(
    "/snapshots/{snapshot_id}/verify",
    response_model=VerificationReportRead,
)
def verify_snapshot(snapshot_id: str, engine: Engine) -> VerificationReportRead:
    return _verification_report(engine.verify_snapshot(snapshot_id=snapshot_id))


# ------------------------------------------------------------------
# Drift detection endpoints
# ------------------------------------------------------------------


def _drift_report(report) -> DriftReportRead:
    return DriftReportRead(
        project_id=report.project_id,
        state=report.state,
        changed_artifacts=report.changed_artifacts,
        affected_knowledge=[
            DriftAffectedKnowledgeRead(
                memory_id=k.memory_id,
                sequence=k.sequence,
                content=k.content,
                reason=k.reason,
            )
            for k in report.affected_knowledge
        ],
        reasons=report.reasons,
    )


@router.post(
    "/projects/{project_id}/drift",
    response_model=DriftReportRead,
)
def detect_drift(
    project_id: str,
    engine: Engine,
    repo_path: str | None = Query(default=None),
) -> DriftReportRead:
    return _drift_report(engine.detect_drift(project_id=project_id, repo_path=repo_path))


# ------------------------------------------------------------------
# Memory decay endpoints
# ------------------------------------------------------------------


def _decay_report(report) -> DecayReportRead:
    return DecayReportRead(
        project_id=report.project_id,
        assessments=[
            DecayAssessmentRead(
                memory_id=assessment.memory_id,
                sequence=assessment.sequence,
                content=assessment.content,
                state=assessment.state,
                freshness=assessment.freshness,
                age_days=assessment.age_days,
                created_at=assessment.created_at,
            )
            for assessment in report.assessments
        ],
        generated_at=report.generated_at,
        fresh_days=report.fresh_days,
        stale_days=report.stale_days,
        stale_count=report.stale_count,
    )


@router.post(
    "/projects/{project_id}/decay",
    response_model=DecayReportRead,
)
def assess_decay(project_id: str, engine: Engine) -> DecayReportRead:
    return _decay_report(engine.assess_decay(project_id=project_id))
