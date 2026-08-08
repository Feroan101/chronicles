from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: datetime


class MemoryVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    memory_id: str
    sequence: int
    content: str
    context: str | None
    created_at: datetime


class MemoryCreate(BaseModel):
    project_id: str
    content: str
    type: str | None = None
    context: str | None = None


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    type: str | None
    created_at: datetime
    versions: list[MemoryVersionRead]


class MemoryUpdate(BaseModel):
    type: str | None = None


class VersionCreate(BaseModel):
    content: str
    context: str | None = None


class MemorySummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    type: str | None
    created_at: datetime


class SearchHitRead(BaseModel):
    memory: MemorySummaryRead
    version: MemoryVersionRead
    rank: float
