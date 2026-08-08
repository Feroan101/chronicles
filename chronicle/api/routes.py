from fastapi import APIRouter, Query

from chronicle.api.deps import Engine
from chronicle.api.schemas import (
    ConfidenceRead,
    ConfidenceRecord,
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
    VersionCreate,
)
from chronicle.core import (
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
def list_memories(project_id: str, engine: Engine) -> list[MemoryRead]:
    memories = engine.list_memories(project_id)
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
) -> list[SearchHitRead]:
    results = engine.search(query=query, project_id=project_id)
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
        engine.create_snapshot(project_id=project_id, message=payload.message)
    )


@router.get("/projects/{project_id}/snapshots", response_model=list[SnapshotRead])
def list_snapshots(project_id: str, engine: Engine) -> list[SnapshotRead]:
    return [SnapshotRead.model_validate(snapshot) for snapshot in engine.list_snapshots(project_id)]


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
