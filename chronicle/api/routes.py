from fastapi import APIRouter, Query

from chronicle.api.deps import Engine
from chronicle.api.schemas import (
    MemoryCreate,
    MemoryRead,
    MemorySummaryRead,
    MemoryUpdate,
    MemoryVersionRead,
    ProjectCreate,
    ProjectRead,
    SearchHitRead,
    VersionCreate,
)
from chronicle.core import (
    ChronicleEngine,
    MemoryNotFoundError,
    ProjectNotFoundError,
)

router = APIRouter()


def _memory_read(engine: ChronicleEngine, memory_id: str) -> MemoryRead:
    memory = engine.get_memory(memory_id)
    if memory is None:
        raise MemoryNotFoundError(memory_id)
    return MemoryRead.model_validate(memory)


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
        engine.create_version(memory_id=memory_id, content=payload.content, context=payload.context)
    )


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
