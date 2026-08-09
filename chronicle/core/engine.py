from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

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
    SnapshotNotFoundError,
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


@dataclass(frozen=True)
class VerificationResult:
    """Result of a single verification check."""

    check: str
    outcome: str  # "verified", "inconclusive", "failed"
    message: str


@dataclass(frozen=True)
class VerificationReport:
    """Report produced by a verification run."""

    scope: str  # "project", "memory", "snapshot"
    scope_id: str
    results: list[VerificationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.outcome == "verified" for r in self.results)

    @property
    def has_failures(self) -> bool:
        return any(r.outcome == "failed" for r in self.results)


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

    # ------------------------------------------------------------------
    # Verification operations
    # ------------------------------------------------------------------

    def verify_project(self, project_id: str) -> VerificationReport:
        """Verify all knowledge in a Project.

        Checks every Memory's version integrity, traceability, and all
        Relationship consistency within the Project.
        """
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)

            results: list[VerificationResult] = []
            memories = MemoryRepository(session).list_by_project(project_id)
            memory_ids = {m.id for m in memories}

            for memory in memories:
                results.extend(self._verify_memory_in_session(session, memory, memory_ids))

            relationships = RelationshipRepository(session).list_by_project(project_id)
            for rel in relationships:
                results.extend(self._verify_relationship_in_session(session, rel, memory_ids))

            return VerificationReport(scope="project", scope_id=project_id, results=results)

    def verify_memory(self, memory_id: str) -> VerificationReport:
        """Verify a single Memory and its Relationships."""
        with self._transaction() as session:
            memory = MemoryRepository(session).get(memory_id)
            if memory is None:
                raise MemoryNotFoundError(memory_id)

            results: list[VerificationResult] = []
            memory_ids = {memory_id}
            results.extend(self._verify_memory_in_session(session, memory, memory_ids))

            relationships = RelationshipRepository(session).list_by_memory(memory_id)
            for rel in relationships:
                results.extend(self._verify_relationship_in_session(session, rel, memory_ids))

            return VerificationReport(scope="memory", scope_id=memory_id, results=results)

    def verify_version(self, memory_id: str, sequence: int) -> VerificationReport:
        """Verify a single Memory Version against its available evidence.

        Reports whether the target version exists within an ordered history
        and whether its origin can be established from stored evidence.
        """
        with self._transaction() as session:
            memory = MemoryRepository(session).get(memory_id)
            if memory is None:
                raise MemoryNotFoundError(memory_id)
            version = MemoryVersionRepository(session).get_by_sequence(memory_id, sequence)
            if version is None:
                raise MemoryVersionNotFoundError(memory_id, sequence)

            results: list[VerificationResult] = []

            # Version integrity: the target version is part of an ordered history
            versions = MemoryVersionRepository(session).list_by_memory(memory_id)
            sequences = [v.sequence for v in versions]
            expected = list(range(1, len(versions) + 1))
            if sequences != expected:
                results.append(
                    VerificationResult(
                        check="version_sequence_order",
                        outcome="failed",
                        message=(
                            f"Memory {memory_id} has unexpected version sequence: {sequences}"
                        ),
                    )
                )
            else:
                results.append(
                    VerificationResult(
                        check="version_sequence_order",
                        outcome="verified",
                        message=f"Memory {memory_id} versions are sequentially ordered",
                    )
                )

            # Traceability: the target version preserves its origin
            has_evidence = len(list(version.evidence)) > 0
            has_context = version.context is not None
            has_type = memory.type is not None
            if has_evidence or has_context or has_type:
                results.append(
                    VerificationResult(
                        check="traceability",
                        outcome="verified",
                        message=(
                            f"Version v{sequence} of memory {memory_id} has origin information"
                        ),
                    )
                )
            else:
                results.append(
                    VerificationResult(
                        check="traceability",
                        outcome="inconclusive",
                        message=(
                            f"Version v{sequence} of memory {memory_id} has no "
                            "evidence or context — origin cannot be established"
                        ),
                    )
                )

            return VerificationReport(
                scope="version",
                scope_id=f"{memory_id}:{sequence}",
                results=results,
            )

    def verify_snapshot(self, snapshot_id: str) -> VerificationReport:
        """Verify a Snapshot's captured state against current knowledge."""
        with self._transaction() as session:
            snapshot = SnapshotRepository(session).get(snapshot_id)
            if snapshot is None:
                raise SnapshotNotFoundError(snapshot_id)

            results: list[VerificationResult] = []

            # Verify each captured version still exists
            for member in snapshot.members:
                version = MemoryVersionRepository(session).get(member.memory_version_id)
                if version is None:
                    results.append(
                        VerificationResult(
                            check="snapshot_member_version_exists",
                            outcome="failed",
                            message=(
                                f"Snapshot member references missing version "
                                f"{member.memory_version_id}"
                            ),
                        )
                    )
                else:
                    results.append(
                        VerificationResult(
                            check="snapshot_member_version_exists",
                            outcome="verified",
                            message=f"Version {version.id} exists (v{version.sequence})",
                        )
                    )

            # Verify each captured relationship still exists
            for snap_rel in snapshot.snapshot_relationships:
                rel = RelationshipRepository(session).get(snap_rel.relationship_id)
                if rel is None:
                    results.append(
                        VerificationResult(
                            check="snapshot_relationship_exists",
                            outcome="failed",
                            message=(
                                f"Snapshot relationship references missing "
                                f"relationship {snap_rel.relationship_id}"
                            ),
                        )
                    )
                else:
                    results.append(
                        VerificationResult(
                            check="snapshot_relationship_exists",
                            outcome="verified",
                            message=f"Relationship {rel.id} exists",
                        )
                    )

            return VerificationReport(scope="snapshot", scope_id=snapshot_id, results=results)

    def _verify_memory_in_session(
        self,
        session: Session,
        memory: Memory,
        known_memory_ids: set[str],
    ) -> list[VerificationResult]:
        """Verify a single Memory within an existing session."""
        results: list[VerificationResult] = []

        # Version integrity: at least one version
        versions = MemoryVersionRepository(session).list_by_memory(memory.id)
        if not versions:
            results.append(
                VerificationResult(
                    check="version_integrity",
                    outcome="failed",
                    message=f"Memory {memory.id} has no versions",
                )
            )
            return results

        results.append(
            VerificationResult(
                check="version_integrity",
                outcome="verified",
                message=f"Memory {memory.id} has {len(versions)} version(s)",
            )
        )

        # Version integrity: sequences are ordered and start at 1
        sequences = [v.sequence for v in versions]
        expected = list(range(1, len(versions) + 1))
        if sequences != expected:
            results.append(
                VerificationResult(
                    check="version_sequence_order",
                    outcome="failed",
                    message=(f"Memory {memory.id} has unexpected version sequence: {sequences}"),
                )
            )
        else:
            results.append(
                VerificationResult(
                    check="version_sequence_order",
                    outcome="verified",
                    message=f"Memory {memory.id} versions are sequentially ordered",
                )
            )

        # Traceability: at least one version has evidence or context
        current_version = versions[-1]
        has_evidence = len(list(current_version.evidence)) > 0
        has_context = current_version.context is not None
        has_type = memory.type is not None
        if has_evidence or has_context or has_type:
            results.append(
                VerificationResult(
                    check="traceability",
                    outcome="verified",
                    message=f"Memory {memory.id} has origin information",
                )
            )
        else:
            results.append(
                VerificationResult(
                    check="traceability",
                    outcome="inconclusive",
                    message=(
                        f"Memory {memory.id} has no evidence, context, "
                        f"or type — origin cannot be established"
                    ),
                )
            )

        return results

    def _verify_relationship_in_session(
        self,
        session: Session,
        rel: Relationship,
        known_memory_ids: set[str],
    ) -> list[VerificationResult]:
        """Verify a single Relationship within an existing session."""
        results: list[VerificationResult] = []

        # Both memories must exist in the same project
        from_ok = rel.from_memory_id in known_memory_ids
        to_ok = rel.to_memory_id in known_memory_ids

        if from_ok and to_ok:
            results.append(
                VerificationResult(
                    check="relationship_consistency",
                    outcome="verified",
                    message=(
                        f"Relationship {rel.id} connects existing memories within the project"
                    ),
                )
            )
        else:
            missing = []
            if not from_ok:
                missing.append(f"from={rel.from_memory_id}")
            if not to_ok:
                missing.append(f"to={rel.to_memory_id}")
            results.append(
                VerificationResult(
                    check="relationship_consistency",
                    outcome="failed",
                    message=(
                        f"Relationship {rel.id} references missing memory: {', '.join(missing)}"
                    ),
                )
            )

        return results
