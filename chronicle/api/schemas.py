from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: datetime


class GitContextCreate(BaseModel):
    branch: str | None = None
    commit: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if not any([self.branch, self.commit, self.description]):
            raise ValueError("at least one of branch, commit, or description must be provided")
        return self


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    memory_version_id: str
    evidence_type: str
    ref: str
    recorded_at: datetime


class MemoryVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    memory_id: str
    sequence: int
    content: str
    context: str | None
    created_at: datetime
    git_context: dict[str, str] | None = None


class MemoryCreate(BaseModel):
    project_id: str
    content: str
    type: str | None = None
    context: str | None = None
    git_context: GitContextCreate | None = None


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
    git_context: GitContextCreate | None = None


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
