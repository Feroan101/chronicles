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


# ------------------------------------------------------------------
# Branch schemas
# ------------------------------------------------------------------


class BranchCreate(BaseModel):
    name: str
    source_branch_id: str | None = None


class BranchSwitch(BaseModel):
    name: str


class BranchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    is_default: bool
    created_at: datetime


class BranchKnowledgeRead(BaseModel):
    memory: MemorySummaryRead
    version: MemoryVersionRead


# ------------------------------------------------------------------
# Observation schemas
# ------------------------------------------------------------------


class ObservationCreate(BaseModel):
    content: str


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    content: str
    status: str
    created_at: datetime
    processed_at: datetime | None


class ObservationProcess(BaseModel):
    action: str
    memory_id: str | None = None


# ------------------------------------------------------------------
# Relationship schemas
# ------------------------------------------------------------------


class RelationshipCreate(BaseModel):
    from_memory_id: str
    to_memory_id: str
    type: str


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    from_memory_id: str
    to_memory_id: str
    type: str
    created_at: datetime


# ------------------------------------------------------------------
# Snapshot schemas
# ------------------------------------------------------------------


class SnapshotCreate(BaseModel):
    message: str | None = None
    branch_id: str | None = None


class SnapshotMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    memory_version_id: str


class SnapshotRelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    relationship_id: str
    from_memory_id: str
    to_memory_id: str
    type: str


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    parent_id: str | None
    branch_id: str | None
    message: str | None
    created_at: datetime
    members: list[SnapshotMemberRead]
    snapshot_relationships: list[SnapshotRelationshipRead]


# ------------------------------------------------------------------
# Confidence schemas
# ------------------------------------------------------------------


class ConfidenceRecord(BaseModel):
    score: float
    reason: str | None = None


class ConfidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    memory_version_id: str
    score: float
    reason: str | None
    recorded_at: datetime


# ------------------------------------------------------------------
# Verification schemas
# ------------------------------------------------------------------


class VerificationResultRead(BaseModel):
    check: str
    outcome: str
    message: str


class VerificationReportRead(BaseModel):
    scope: str
    scope_id: str
    results: list[VerificationResultRead]
    passed: bool
    has_failures: bool


# ------------------------------------------------------------------
# Drift detection schemas
# ------------------------------------------------------------------


class DriftAffectedKnowledgeRead(BaseModel):
    memory_id: str
    sequence: int
    content: str
    reason: str


class DriftReportRead(BaseModel):
    project_id: str
    state: str
    changed_artifacts: list[str]
    affected_knowledge: list[DriftAffectedKnowledgeRead]
    reasons: list[str]


# ------------------------------------------------------------------
# Memory decay schemas
# ------------------------------------------------------------------


class DecayAssessmentRead(BaseModel):
    memory_id: str
    sequence: int
    content: str
    state: str
    freshness: float
    age_days: float
    created_at: datetime


class DecayReportRead(BaseModel):
    project_id: str
    assessments: list[DecayAssessmentRead]
    generated_at: datetime
    fresh_days: int
    stale_days: int
    stale_count: int
