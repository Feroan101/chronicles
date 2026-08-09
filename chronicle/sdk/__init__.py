"""Chronicle Python SDK.

A thin, synchronous adapter over ``ChronicleEngine`` for embedding Chronicle
directly into applications and AI agent systems.

Canonical usage::

    from chronicle.sdk import Chronicle

    chronicle = Chronicle()  # or Chronicle(db_path=...), Chronicle(session_factory=...)
    project = chronicle.create_project(name="demo")

The SDK exposes no SQLAlchemy objects and contains no business logic; it
delegates every operation to ``ChronicleEngine`` and returns the shared
Pydantic read models also used by the REST and MCP interfaces.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from chronicle.api.schemas import (
    ConfidenceRead,
    DriftAffectedKnowledgeRead,
    DriftReportRead,
    EvidenceRead,
    MemoryRead,
    MemorySummaryRead,
    MemoryVersionRead,
    ObservationRead,
    ProjectRead,
    RelationshipRead,
    SearchHitRead,
    SnapshotRead,
    VerificationReportRead,
    VerificationResultRead,
)
from chronicle.core import (
    ChronicleEngine,
    ChronicleError,
    ConfidenceScoreRangeError,
    CrossProjectRelationshipError,
    GitContext,
    GitContextError,
    InvalidObservationActionError,
    MemoryNotFoundError,
    MemoryVersionNotFoundError,
    ObservationAlreadyProcessedError,
    ObservationNotFoundError,
    ProjectNotFoundError,
    RelationshipNotFoundError,
    SearchQueryError,
    SelfRelationshipError,
    SnapshotNotFoundError,
)

DEFAULT_DB_PATH = Path(".chronicle") / "chronicle.db"


class _UnsetType:
    """Marker for an argument that was not provided.

    ``update_memory`` uses this to distinguish "leave the value unchanged"
    from an explicit ``None`` (which clears the value).
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = _UnsetType()


def _project(project) -> ProjectRead:
    return ProjectRead.model_validate(project)


def _memory(memory) -> MemoryRead:
    return MemoryRead.model_validate(memory)


def _version(version) -> MemoryVersionRead:
    return MemoryVersionRead.model_validate(version)


def _search_hit(result) -> SearchHitRead:
    return SearchHitRead(
        memory=MemorySummaryRead.model_validate(result.memory),
        version=MemoryVersionRead.model_validate(result.version),
        rank=result.rank,
    )


def _observation(observation) -> ObservationRead:
    return ObservationRead.model_validate(observation)


def _relationship(relationship) -> RelationshipRead:
    return RelationshipRead.model_validate(relationship)


def _snapshot(snapshot) -> SnapshotRead:
    return SnapshotRead.model_validate(snapshot)


class Chronicle:
    """Programmatic access to Chronicle.

    The client is a thin adapter over ``ChronicleEngine``. Each instance
    holds its own engine and store connection; you may open more than one
    connection at a time. The store must already exist and be migrated — the
    SDK never creates or migrates the database automatically.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        """Connect to a Chronicle store.

        ``session_factory`` wins over ``db_path`` when both are given.
        With no explicit configuration the default store is
        ``.chronicle/chronicle.db`` relative to the current working
        directory, matching the REST and MCP interfaces.
        """
        if session_factory is None:
            path = db_path if db_path is not None else DEFAULT_DB_PATH
            database = create_engine(f"sqlite:///{path}")
            session_factory = sessionmaker(bind=database)
        self._engine = ChronicleEngine(session_factory)

    def create_project(self, name: str, description: str | None = None) -> ProjectRead:
        """Create a new project and return its read model."""
        return _project(self._engine.create_project(name=name, description=description))

    def get_project(self, project_id: str) -> ProjectRead:
        """Get a project by ID.

        Raises ``ProjectNotFoundError`` if no such project exists.
        """
        project = self._engine.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return _project(project)

    def create_memory(
        self,
        project_id: str,
        content: str,
        type: str | None = None,
        context: str | None = None,
        git_branch: str | None = None,
        git_commit: str | None = None,
        git_description: str | None = None,
    ) -> MemoryRead:
        """Store a new memory in a project, with its first version."""
        git_ctx = None
        if any([git_branch, git_commit, git_description]):
            git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
        return _memory(
            self._engine.create_memory(
                project_id=project_id,
                content=content,
                type=type,
                context=context,
                git_context=git_ctx,
            )
        )

    def get_memory(self, memory_id: str) -> MemoryRead:
        """Get a memory and its version history by ID.

        Raises ``MemoryNotFoundError`` if no such memory exists.
        """
        memory = self._engine.get_memory(memory_id)
        if memory is None:
            raise MemoryNotFoundError(memory_id)
        return _memory(memory)

    def list_memories(self, project_id: str) -> list[MemoryRead]:
        """List all memories in a project, ordered by creation."""
        return [_memory(memory) for memory in self._engine.list_memories(project_id)]

    def update_memory(self, memory_id: str, type: str | None = UNSET) -> MemoryRead:
        """Update the type of a memory.

        Omitting ``type`` (the default) leaves the type unchanged. Passing an
        explicit ``None`` clears the type.
        """
        if type is not UNSET:
            memory = self._engine.update_memory(memory_id=memory_id, type=type)
        else:
            memory = self._engine.update_memory(memory_id=memory_id)
        return _memory(memory)

    def create_version(
        self,
        memory_id: str,
        content: str,
        context: str | None = None,
        git_branch: str | None = None,
        git_commit: str | None = None,
        git_description: str | None = None,
    ) -> MemoryVersionRead:
        """Append a new version of a memory."""
        git_ctx = None
        if any([git_branch, git_commit, git_description]):
            git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
        return _version(
            self._engine.create_version(
                memory_id=memory_id,
                content=content,
                context=context,
                git_context=git_ctx,
            )
        )

    def get_evidence(self, memory_id: str, sequence: int) -> list[EvidenceRead]:
        """Get evidence attached to a specific version."""
        evidence = self._engine.get_evidence(memory_id=memory_id, sequence=sequence)
        return [EvidenceRead.model_validate(e) for e in evidence]

    def search(self, query: str, project_id: str | None = None) -> list[SearchHitRead]:
        """Search project knowledge, returning the current version of matches."""
        return [
            _search_hit(result)
            for result in self._engine.search(query=query, project_id=project_id)
        ]

    # ------------------------------------------------------------------
    # Observation methods
    # ------------------------------------------------------------------

    def create_observation(self, project_id: str, content: str) -> ObservationRead:
        """Create a pending observation in a project."""
        return _observation(self._engine.create_observation(project_id=project_id, content=content))

    def list_observations(self, project_id: str) -> list[ObservationRead]:
        """List all observations in a project, ordered by creation."""
        return [_observation(obs) for obs in self._engine.list_observations(project_id)]

    def process_observation(
        self,
        observation_id: str,
        action: str,
        memory_id: str | None = None,
    ) -> ObservationRead:
        """Process an observation into knowledge or discard it.

        Actions: "create_memory", "update_memory", "discard".
        For "update_memory", ``memory_id`` is required.
        """
        return _observation(
            self._engine.process_observation(
                observation_id=observation_id,
                action=action,
                memory_id=memory_id,
            )
        )

    # ------------------------------------------------------------------
    # Relationship methods
    # ------------------------------------------------------------------

    def create_relationship(
        self,
        project_id: str,
        from_memory_id: str,
        to_memory_id: str,
        type: str,
    ) -> RelationshipRead:
        """Create a directed relationship between two memories."""
        return _relationship(
            self._engine.create_relationship(
                project_id=project_id,
                from_memory_id=from_memory_id,
                to_memory_id=to_memory_id,
                type=type,
            )
        )

    def list_relationships(self, project_id: str) -> list[RelationshipRead]:
        """List all relationships in a project, ordered by creation."""
        return [_relationship(rel) for rel in self._engine.list_relationships(project_id)]

    def get_relationships_for_memory(self, memory_id: str) -> list[RelationshipRead]:
        """Get all relationships where a memory is source or target."""
        return [_relationship(rel) for rel in self._engine.get_relationships_for_memory(memory_id)]

    def remove_relationship(self, relationship_id: str) -> None:
        """Remove a relationship."""
        self._engine.remove_relationship(relationship_id)

    # ------------------------------------------------------------------
    # Snapshot methods
    # ------------------------------------------------------------------

    def create_snapshot(self, project_id: str, message: str | None = None) -> SnapshotRead:
        """Create a snapshot of the project's current knowledge state."""
        return _snapshot(self._engine.create_snapshot(project_id=project_id, message=message))

    def get_snapshot(self, snapshot_id: str) -> SnapshotRead:
        """Get a snapshot by ID.

        Raises ``SnapshotNotFoundError`` if no such snapshot exists.
        """
        snapshot = self._engine.get_snapshot(snapshot_id)
        if snapshot is None:
            raise SnapshotNotFoundError(snapshot_id)
        return _snapshot(snapshot)

    def list_snapshots(self, project_id: str) -> list[SnapshotRead]:
        """List all snapshots for a project."""
        return [_snapshot(snapshot) for snapshot in self._engine.list_snapshots(project_id)]

    # ------------------------------------------------------------------
    # Confidence methods
    # ------------------------------------------------------------------

    def record_confidence(
        self,
        memory_id: str,
        sequence: int,
        score: float,
        reason: str | None = None,
    ) -> ConfidenceRead:
        """Record a confidence score for a specific memory version.

        Scores must be between 0.0 and 1.0 inclusive.
        """
        return ConfidenceRead.model_validate(
            self._engine.record_confidence(
                memory_id=memory_id, sequence=sequence, score=score, reason=reason
            )
        )

    def get_confidence(self, memory_id: str, sequence: int) -> ConfidenceRead | None:
        """Get the current confidence score for a memory version.

        Returns None if no confidence has been recorded.
        """
        score = self._engine.get_confidence(memory_id=memory_id, sequence=sequence)
        if score is None:
            return None
        return ConfidenceRead.model_validate(score)

    def get_confidence_history(self, memory_id: str, sequence: int) -> list[ConfidenceRead]:
        """Get the full confidence history for a memory version."""
        return [
            ConfidenceRead.model_validate(s)
            for s in self._engine.get_confidence_history(memory_id=memory_id, sequence=sequence)
        ]

    # ------------------------------------------------------------------
    # Verification methods
    # ------------------------------------------------------------------

    def verify_project(self, project_id: str) -> VerificationReportRead:
        """Verify all knowledge in a project.

        Checks version integrity, traceability, and relationship consistency.
        """
        report = self._engine.verify_project(project_id=project_id)
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

    def verify_memory(self, memory_id: str) -> VerificationReportRead:
        """Verify a single memory and its relationships."""
        report = self._engine.verify_memory(memory_id=memory_id)
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

    def verify_version(self, memory_id: str, sequence: int) -> VerificationReportRead:
        """Verify a single memory version against its available evidence."""
        report = self._engine.verify_version(memory_id=memory_id, sequence=sequence)
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

    def verify_snapshot(self, snapshot_id: str) -> VerificationReportRead:
        """Verify a snapshot's captured state against current knowledge."""
        report = self._engine.verify_snapshot(snapshot_id=snapshot_id)
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

    # ------------------------------------------------------------------
    # Drift detection methods
    # ------------------------------------------------------------------

    def detect_drift(
        self,
        project_id: str,
        repo_path: str | Path | None = None,
    ) -> DriftReportRead:
        """Detect whether a project's knowledge may have drifted.

        Compares the current Git state against the evidence recorded for the
        project's knowledge. Read-only; never modifies knowledge.
        """
        report = self._engine.detect_drift(project_id=project_id, repo_path=repo_path)
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


__all__ = [
    "Chronicle",
    "UNSET",
    "ChronicleError",
    "ConfidenceScoreRangeError",
    "CrossProjectRelationshipError",
    "DriftAffectedKnowledgeRead",
    "DriftReportRead",
    "GitContext",
    "GitContextError",
    "InvalidObservationActionError",
    "MemoryNotFoundError",
    "MemoryVersionNotFoundError",
    "ObservationAlreadyProcessedError",
    "ObservationNotFoundError",
    "ProjectNotFoundError",
    "RelationshipNotFoundError",
    "SearchQueryError",
    "SelfRelationshipError",
    "SnapshotNotFoundError",
    "ConfidenceRead",
    "EvidenceRead",
    "MemoryRead",
    "MemorySummaryRead",
    "MemoryVersionRead",
    "ObservationRead",
    "ProjectRead",
    "RelationshipRead",
    "SearchHitRead",
    "SnapshotRead",
    "VerificationReportRead",
    "VerificationResultRead",
]
