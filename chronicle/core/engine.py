from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from chronicle.core.errors import (
    ConfidenceScoreRangeError,
    CrossProjectRelationshipError,
    InvalidObservationActionError,
    MemoryNotFoundError,
    MemoryVersionNotFoundError,
    ObservationAlreadyProcessedError,
    ObservationNotFoundError,
    ProjectNotFoundError,
    RelationshipNotFoundError,
    SearchQueryError,
    SelfRelationshipError,
)
from chronicle.core.git import GitContext
from chronicle.models import (
    ConfidenceScore,
    Evidence,
    Memory,
    MemoryVersion,
    Observation,
    Project,
    Relationship,
    Snapshot,
    SnapshotMember,
    SnapshotRelationship,
)
from chronicle.storage import (
    ConfidenceRepository,
    EvidenceRepository,
    MemoryRepository,
    MemoryVersionRepository,
    ObservationRepository,
    ProjectRepository,
    RelationshipRepository,
    SnapshotMemberRepository,
    SnapshotRelationshipRepository,
    SnapshotRepository,
)
from chronicle.utils.ids import new_uuid
from chronicle.utils.time import utcnow

_UNSET = object()


@dataclass(frozen=True)
class SearchResult:
    """A Memory matched by search, together with its Current Version."""

    memory: Memory
    version: MemoryVersion
    rank: float


class ChronicleEngine:
    """Chronicle Core: business operations built on the storage layer."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        session = self._session_factory()
        session.expire_on_commit = False
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_project(self, name: str, description: str | None = None) -> Project:
        with self._transaction() as session:
            project = Project(id=new_uuid(), name=name, description=description)
            return ProjectRepository(session).create(project)

    def get_project(self, project_id: str) -> Project | None:
        with self._transaction() as session:
            return ProjectRepository(session).get(project_id)

    def create_memory(
        self,
        project_id: str,
        content: str,
        type: str | None = None,
        context: str | None = None,
        git_context: GitContext | None = None,
    ) -> Memory:
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            memory = Memory(id=new_uuid(), project_id=project_id, type=type)
            MemoryRepository(session).create(memory)
            version = MemoryVersion(
                id=new_uuid(),
                memory_id=memory.id,
                sequence=1,
                content=content,
                context=context,
            )
            MemoryVersionRepository(session).create(version)
            self._record_git_context(session, version, git_context)
            session.flush()
            _ = memory.versions
            for v in memory.versions:
                _ = v.evidence
            return memory

    def get_memory(self, memory_id: str) -> Memory | None:
        with self._transaction() as session:
            return MemoryRepository(session).get(memory_id)

    def update_memory(self, memory_id: str, type: str | None = _UNSET) -> Memory:
        with self._transaction() as session:
            memory = MemoryRepository(session).get(memory_id)
            if memory is None:
                raise MemoryNotFoundError(memory_id)
            if type is not _UNSET:
                memory.type = type
            return memory

    def create_version(
        self,
        memory_id: str,
        content: str,
        context: str | None = None,
        git_context: GitContext | None = None,
    ) -> MemoryVersion:
        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            next_sequence = MemoryVersionRepository(session).highest_sequence(memory_id) + 1
            version = MemoryVersion(
                id=new_uuid(),
                memory_id=memory_id,
                sequence=next_sequence,
                content=content,
                context=context,
            )
            MemoryVersionRepository(session).create(version)
            self._record_git_context(session, version, git_context)
            session.flush()
            _ = version.evidence
            return version

    def list_memories(self, project_id: str) -> list[Memory]:
        with self._transaction() as session:
            return MemoryRepository(session).list_by_project(project_id)

    def get_version(self, memory_id: str, sequence: int) -> MemoryVersion | None:
        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            return MemoryVersionRepository(session).get_by_sequence(memory_id, sequence)

    def get_evidence(self, memory_id: str, sequence: int) -> list[Evidence]:
        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            version = MemoryVersionRepository(session).get_by_sequence(memory_id, sequence)
            if version is None:
                return []
            return list(version.evidence)

    @staticmethod
    def _record_git_context(
        session: Session, version: MemoryVersion, git_context: GitContext | None
    ) -> None:
        if git_context is None:
            return
        repo = EvidenceRepository(session)
        fields = {
            "branch": git_context.branch,
            "commit": git_context.commit,
            "description": git_context.description,
        }
        for evidence_type, ref in fields.items():
            if ref is not None:
                repo.create(
                    Evidence(
                        id=new_uuid(),
                        memory_version_id=version.id,
                        evidence_type=evidence_type,
                        ref=ref,
                        recorded_at=utcnow(),
                    )
                )

    def search(self, query: str, project_id: str | None = None) -> list[SearchResult]:
        """Search Memories by keyword content.

        Only the Current Version of each Memory is returned, and each Memory
        appears at most once. When ``project_id`` is supplied, results are
        restricted to that Project.
        """
        if not query or not query.strip():
            raise SearchQueryError(query)
        if '"' in query:
            raise SearchQueryError(query)
        with self._transaction() as session:
            try:
                rows = MemoryRepository(session).search(query, project_id)
            except OperationalError as exc:
                raise SearchQueryError(query, detail=str(exc)) from exc
            current_sequences = MemoryVersionRepository(session).highest_sequences(
                [memory.id for memory, _, _ in rows]
            )
            results = []
            for memory, version, rank in rows:
                if version.sequence != current_sequences.get(memory.id):
                    continue
                results.append(SearchResult(memory=memory, version=version, rank=rank))
            return results

    # ------------------------------------------------------------------
    # Observation operations
    # ------------------------------------------------------------------

    def create_observation(self, project_id: str, content: str) -> Observation:
        """Create a pending Observation in a Project."""
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            observation = Observation(
                id=new_uuid(),
                project_id=project_id,
                content=content,
                status="pending",
            )
            return ObservationRepository(session).create(observation)

    def list_observations(self, project_id: str) -> list[Observation]:
        """List all Observations in a Project, ordered by creation."""
        with self._transaction() as session:
            return ObservationRepository(session).list_by_project(project_id)

    def process_observation(
        self,
        observation_id: str,
        action: str,
        memory_id: str | None = None,
    ) -> Observation:
        """Process an Observation into persistent knowledge or discard it.

        Actions:
        - "create_memory": creates a new Memory from the observation content.
        - "update_memory": appends a new Version to an existing Memory
          (``memory_id`` is required).
        - "discard": marks the Observation as discarded with no knowledge change.
        """
        valid_actions = {"create_memory", "update_memory", "discard"}
        if action not in valid_actions:
            raise InvalidObservationActionError(action)

        with self._transaction() as session:
            observation = ObservationRepository(session).get(observation_id)
            if observation is None:
                raise ObservationNotFoundError(observation_id)
            if observation.status != "pending":
                raise ObservationAlreadyProcessedError(observation_id, observation.status)

            if action == "create_memory":
                memory = Memory(
                    id=new_uuid(),
                    project_id=observation.project_id,
                    type=None,
                )
                MemoryRepository(session).create(memory)
                version = MemoryVersion(
                    id=new_uuid(),
                    memory_id=memory.id,
                    sequence=1,
                    content=observation.content,
                    context=None,
                )
                MemoryVersionRepository(session).create(version)
                session.flush()
                _ = memory.versions

            elif action == "update_memory":
                if memory_id is None:
                    raise MemoryNotFoundError("(none)")
                memory = MemoryRepository(session).get(memory_id)
                if memory is None:
                    raise MemoryNotFoundError(memory_id)
                if memory.project_id != observation.project_id:
                    raise CrossProjectRelationshipError()
                next_seq = MemoryVersionRepository(session).highest_sequence(memory_id) + 1
                version = MemoryVersion(
                    id=new_uuid(),
                    memory_id=memory_id,
                    sequence=next_seq,
                    content=observation.content,
                    context=None,
                )
                MemoryVersionRepository(session).create(version)

            # action == "discard": no knowledge change

            ObservationRepository(session).update_status(
                observation_id,
                "processed" if action != "discard" else "discarded",
                processed_at=utcnow(),
            )
            return observation

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------

    def create_relationship(
        self,
        project_id: str,
        from_memory_id: str,
        to_memory_id: str,
        type: str,
    ) -> Relationship:
        """Create a directed, typed Relationship between two Memories."""
        if from_memory_id == to_memory_id:
            raise SelfRelationshipError(from_memory_id)

        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)

            from_memory = MemoryRepository(session).get(from_memory_id)
            if from_memory is None:
                raise MemoryNotFoundError(from_memory_id)
            if from_memory.project_id != project_id:
                raise CrossProjectRelationshipError()

            to_memory = MemoryRepository(session).get(to_memory_id)
            if to_memory is None:
                raise MemoryNotFoundError(to_memory_id)
            if to_memory.project_id != project_id:
                raise CrossProjectRelationshipError()

            relationship = Relationship(
                id=new_uuid(),
                project_id=project_id,
                from_memory_id=from_memory_id,
                to_memory_id=to_memory_id,
                type=type,
            )
            return RelationshipRepository(session).create(relationship)

    def list_relationships(self, project_id: str) -> list[Relationship]:
        """List all Relationships in a Project, ordered by creation."""
        with self._transaction() as session:
            return RelationshipRepository(session).list_by_project(project_id)

    def get_relationships_for_memory(self, memory_id: str) -> list[Relationship]:
        """Get all Relationships where a Memory is source or target."""
        with self._transaction() as session:
            return RelationshipRepository(session).list_by_memory(memory_id)

    def remove_relationship(self, relationship_id: str) -> None:
        """Remove a Relationship.

        This is a physical delete. Relationship history/versioning is a
        deferred requirement (see GRAPH.md §8, §12).
        """
        with self._transaction() as session:
            if not RelationshipRepository(session).delete(relationship_id):
                raise RelationshipNotFoundError(relationship_id)

    # ------------------------------------------------------------------
    # Snapshot operations
    # ------------------------------------------------------------------

    def create_snapshot(self, project_id: str, message: str | None = None) -> Snapshot:
        """Create a Snapshot of the Project's current knowledge state."""
        with self._transaction() as session:
            project = ProjectRepository(session).get(project_id)
            if project is None:
                raise ProjectNotFoundError(project_id)

            snapshot = Snapshot(
                id=new_uuid(),
                project_id=project_id,
                message=message,
                created_at=utcnow(),
            )
            SnapshotRepository(session).create(snapshot)

            memories = MemoryRepository(session).list_by_project(project_id)
            members: list[SnapshotMember] = []
            for memory in memories:
                current_version = MemoryVersionRepository(session).highest_version(memory.id)
                if current_version is not None:
                    members.append(
                        SnapshotMember(
                            snapshot_id=snapshot.id,
                            memory_version_id=current_version.id,
                        )
                    )
            if members:
                SnapshotMemberRepository(session).create_many(members)

            relationships = RelationshipRepository(session).list_by_project(project_id)
            snapshot_rels: list[SnapshotRelationship] = []
            for rel in relationships:
                snapshot_rels.append(
                    SnapshotRelationship(
                        snapshot_id=snapshot.id,
                        relationship_id=rel.id,
                        from_memory_id=rel.from_memory_id,
                        to_memory_id=rel.to_memory_id,
                        type=rel.type,
                    )
                )
            if snapshot_rels:
                SnapshotRelationshipRepository(session).create_many(snapshot_rels)

            session.flush()
            _ = snapshot.members
            _ = snapshot.snapshot_relationships
            return snapshot

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Retrieve a specific Snapshot."""
        with self._transaction() as session:
            snapshot = SnapshotRepository(session).get(snapshot_id)
            if snapshot is not None:
                _ = snapshot.members
                _ = snapshot.snapshot_relationships
            return snapshot

    def list_snapshots(self, project_id: str) -> list[Snapshot]:
        """List all Snapshots for a Project."""
        with self._transaction() as session:
            snapshots = SnapshotRepository(session).list_by_project(project_id)
            for snapshot in snapshots:
                _ = snapshot.members
                _ = snapshot.snapshot_relationships
            return snapshots

    # ------------------------------------------------------------------
    # Confidence operations
    # ------------------------------------------------------------------

    def record_confidence(
        self,
        memory_id: str,
        sequence: int,
        score: float,
        reason: str | None = None,
    ) -> ConfidenceScore:
        """Record a confidence score for a specific Memory Version.

        Scores must be between 0.0 and 1.0 inclusive. Each call appends
        a new record; the current confidence is the most recent entry.
        """
        if not (0.0 <= score <= 1.0):
            raise ConfidenceScoreRangeError(score)

        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            version = MemoryVersionRepository(session).get_by_sequence(memory_id, sequence)
            if version is None:
                raise MemoryVersionNotFoundError(memory_id, sequence)

            record = ConfidenceScore(
                id=new_uuid(),
                memory_version_id=version.id,
                score=score,
                reason=reason,
                recorded_at=utcnow(),
            )
            return ConfidenceRepository(session).create(record)

    def get_confidence(self, memory_id: str, sequence: int) -> ConfidenceScore | None:
        """Get the current (most recent) confidence score for a Memory Version."""
        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            version = MemoryVersionRepository(session).get_by_sequence(memory_id, sequence)
            if version is None:
                raise MemoryVersionNotFoundError(memory_id, sequence)
            return ConfidenceRepository(session).latest_by_version(version.id)

    def get_confidence_history(self, memory_id: str, sequence: int) -> list[ConfidenceScore]:
        """Get the full confidence history for a Memory Version."""
        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            version = MemoryVersionRepository(session).get_by_sequence(memory_id, sequence)
            if version is None:
                raise MemoryVersionNotFoundError(memory_id, sequence)
            return ConfidenceRepository(session).list_by_version(version.id)
