from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from chronicle.core.errors import (
    BranchNameConflictError,
    BranchNotFoundError,
    ConfidenceScoreRangeError,
    CrossProjectRelationshipError,
    DecayConfigError,
    InvalidObservationActionError,
    MemoryNameAmbiguousError,
    MemoryNameConflictError,
    MemoryNotFoundError,
    MemoryVersionNotFoundError,
    ObservationAlreadyProcessedError,
    ObservationNotFoundError,
    ProjectNameAmbiguousError,
    ProjectNameConflictError,
    ProjectNotFoundError,
    RelationshipNotFoundError,
    SearchQueryError,
    SelfRelationshipError,
    SnapshotNameConflictError,
    SnapshotNotFoundError,
)
from chronicle.core.git import GitContext, GitTree, read_git_tree
from chronicle.models import (
    Branch,
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
    BranchMemberRepository,
    BranchRepository,
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

DEFAULT_BRANCH_NAME = "main"


@dataclass(frozen=True)
class SearchResult:
    """A Memory matched by search, together with its Current Version."""

    memory: Memory
    version: MemoryVersion
    rank: float


@dataclass(frozen=True)
class BranchKnowledge:
    """The Version currently visible for a Memory on a Branch."""

    memory: Memory
    version: MemoryVersion


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


@dataclass(frozen=True)
class DriftAffectedKnowledge:
    """Knowledge whose supporting evidence overlaps a detected change."""

    memory_id: str
    sequence: int
    content: str
    reason: str


@dataclass(frozen=True)
class DriftReport:
    """Report produced by a drift detection run.

    ``state`` is "clean" or "dirty". A dirty tree means the current project
    state differs from the evidence reference state. Affected knowledge is
    knowledge whose evidence overlaps those changes; the report never claims
    that such knowledge is stale.
    """

    project_id: str
    state: str  # "clean" or "dirty"
    changed_artifacts: list[str] = field(default_factory=list)
    affected_knowledge: list[DriftAffectedKnowledge] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return self.state == "clean"

    @property
    def dirty(self) -> bool:
        return self.state == "dirty"


DECAY_FRESH_DAYS = 30
DECAY_STALE_DAYS = 180


@dataclass(frozen=True)
class DecayAssessment:
    """Freshness assessment for a Memory's current Version.

    Decay represents knowledge freshness, not truth: a knowledge item may
    have high confidence but low freshness. ``state`` is "fresh", "aging",
    or "stale"; ``freshness`` is a linear score from 1.0 (just updated) down
    to 0.0 once the Version reaches the stale threshold. Age is measured from
    the Version's ``created_at`` timestamp; nothing is mutated or persisted.
    """

    memory_id: str
    sequence: int
    content: str
    state: str  # "fresh", "aging", or "stale"
    freshness: float  # 0.0 to 1.0
    age_days: float
    created_at: datetime

    @property
    def fresh(self) -> bool:
        return self.state == "fresh"

    @property
    def aging(self) -> bool:
        return self.state == "aging"

    @property
    def stale(self) -> bool:
        return self.state == "stale"


@dataclass(frozen=True)
class DecayReport:
    """Report produced by a decay assessment run."""

    project_id: str
    assessments: list[DecayAssessment] = field(default_factory=list)
    generated_at: datetime = field(default_factory=utcnow)
    fresh_days: int = DECAY_FRESH_DAYS
    stale_days: int = DECAY_STALE_DAYS

    @property
    def stale_count(self) -> int:
        return sum(1 for assessment in self.assessments if assessment.stale)


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


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
            if ProjectRepository(session).get_by_name(name):
                raise ProjectNameConflictError(name)
            project = Project(id=new_uuid(), name=name, description=description)
            ProjectRepository(session).create(project)
            branch = Branch(
                id=new_uuid(),
                project_id=project.id,
                name=DEFAULT_BRANCH_NAME,
                is_default=True,
            )
            BranchRepository(session).create(branch)
            project.default_branch_id = branch.id
            project.current_branch_id = branch.id
            return project

    def get_project(self, project_id: str) -> Project | None:
        with self._transaction() as session:
            return ProjectRepository(session).get(project_id)

    def list_projects(self) -> list[Project]:
        with self._transaction() as session:
            return ProjectRepository(session).list_all()

    def get_project_by_name(self, name: str) -> Project | None:
        with self._transaction() as session:
            return ProjectRepository(session).get_by_name(name)

    def resolve_project(self, name: str) -> Project:
        """Resolve a Project by its human-readable name.

        Raises ``ProjectNotFoundError`` when nothing matches and
        ``ProjectNameAmbiguousError`` when several share the name.
        """
        with self._transaction() as session:
            matches = ProjectRepository(session).list_by_name(name)
            if not matches:
                raise ProjectNotFoundError(name)
            if len(matches) > 1:
                raise ProjectNameAmbiguousError(name)
            return matches[0]

    def create_memory(
        self,
        project_id: str,
        content: str,
        name: str | None = None,
        type: str | None = None,
        context: str | None = None,
        git_context: GitContext | None = None,
        branch_id: str | None = None,
    ) -> Memory:
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            if name is not None and MemoryRepository(session).get_by_name(project_id, name):
                raise MemoryNameConflictError(name)
            target_branch_id = self._resolve_branch_context(session, project_id, branch_id)
            memory = Memory(id=new_uuid(), project_id=project_id, name=name, type=type)
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
            BranchMemberRepository(session).set(target_branch_id, memory.id, version.id)
            return memory

    def get_memory(self, memory_id: str) -> Memory | None:
        with self._transaction() as session:
            return MemoryRepository(session).get(memory_id)

    def get_memory_by_name(self, project_id: str, name: str) -> Memory | None:
        with self._transaction() as session:
            return MemoryRepository(session).get_by_name(project_id, name)

    def resolve_memory(self, name: str, project_id: str | None = None) -> Memory:
        """Resolve a Memory by its human-readable name.

        Within a project the name is unique, so an exact match is returned.
        Without a project the name is searched across all projects; it must
        be unique globally or ``MemoryNameAmbiguousError`` is raised.
        """
        with self._transaction() as session:
            if project_id is not None:
                memory = MemoryRepository(session).get_by_name(project_id, name)
                if memory is None:
                    raise MemoryNotFoundError(name)
                return memory
            matches = MemoryRepository(session).list_by_name(name)
            if not matches:
                raise MemoryNotFoundError(name)
            if len(matches) > 1:
                raise MemoryNameAmbiguousError(name)
            return matches[0]

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
        branch_id: str | None = None,
    ) -> MemoryVersion:
        with self._transaction() as session:
            memory = MemoryRepository(session).get(memory_id)
            if memory is None:
                raise MemoryNotFoundError(memory_id)
            target_branch_id = self._resolve_branch_context(session, memory.project_id, branch_id)
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
            BranchMemberRepository(session).set(target_branch_id, memory_id, version.id)
            return version

    def list_memories(self, project_id: str, branch_id: str | None = None) -> list[Memory]:
        with self._transaction() as session:
            if branch_id is None:
                return MemoryRepository(session).list_by_project(project_id)
            resolved = self._resolve_branch_context(session, project_id, branch_id)
            members = {
                m.memory_id for m in BranchMemberRepository(session).list_by_branch(resolved)
            }
            return [
                memory
                for memory in MemoryRepository(session).list_by_project(project_id)
                if memory.id in members
            ]

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

    def _ensure_default_branch(self, session: Session, project_id: str) -> Branch:
        """Return the Project's default Branch, self-healing legacy Projects.

        Projects created before Branches existed have no default branch. A
        ``main`` Branch is created on demand and set as the default/current
        branch so branch-aware operations always have a context.
        """
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        default = (
            BranchRepository(session).get(project.default_branch_id)
            if project.default_branch_id is not None
            else None
        )
        if default is not None:
            if project.current_branch_id is None:
                project.current_branch_id = default.id
            return default
        existing = BranchRepository(session).get_by_name(project_id, DEFAULT_BRANCH_NAME)
        if existing is not None:
            project.default_branch_id = existing.id
            project.current_branch_id = existing.id
            return existing
        branch = Branch(
            id=new_uuid(),
            project_id=project_id,
            name=DEFAULT_BRANCH_NAME,
            is_default=True,
        )
        BranchRepository(session).create(branch)
        project.default_branch_id = branch.id
        project.current_branch_id = branch.id
        return branch

    def _resolve_branch_context(
        self, session: Session, project_id: str, branch_id: str | None
    ) -> str:
        """Resolve the Branch id used as the knowledge context.

        An explicit ``branch_id`` must belong to the Project; otherwise the
        Project's persisted current Branch is used.
        """
        if branch_id is not None:
            branch = BranchRepository(session).get(branch_id)
            if branch is None or branch.project_id != project_id:
                raise BranchNotFoundError(branch_id)
            return branch.id
        self._ensure_default_branch(session, project_id)
        project = ProjectRepository(session).get(project_id)
        branch = BranchRepository(session).get(
            project.current_branch_id or project.default_branch_id
        )
        if branch is None:
            raise BranchNotFoundError(project.default_branch_id or "(none)")
        return branch.id

    def search(
        self,
        query: str,
        project_id: str | None = None,
        branch_id: str | None = None,
    ) -> list[SearchResult]:
        """Search Memories by keyword content.

        Only the Current Version of each Memory is returned, and each Memory
        appears at most once. When ``project_id`` is supplied, results are
        restricted to that Project. When ``branch_id`` is supplied, results are
        restricted to that Branch's current knowledge state.
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

            if branch_id is None:
                current_sequences = MemoryVersionRepository(session).highest_sequences(
                    [memory.id for memory, _, _ in rows]
                )
                results = []
                for memory, version, rank in rows:
                    if version.sequence != current_sequences.get(memory.id):
                        continue
                    results.append(SearchResult(memory=memory, version=version, rank=rank))
                return results

            branch = BranchRepository(session).get(branch_id)
            if branch is None:
                raise BranchNotFoundError(branch_id)
            if project_id is not None and project_id != branch.project_id:
                raise BranchNotFoundError(branch_id)

            member_versions = {
                member.memory_id: member.memory_version_id
                for member in BranchMemberRepository(session).list_by_branch(branch.id)
            }
            results: list[SearchResult] = []
            seen: set[str] = set()
            for memory, version, rank in rows:
                if project_id is None and memory.project_id != branch.project_id:
                    continue
                if member_versions.get(memory.id) != version.id:
                    continue
                if memory.id in seen:
                    continue
                seen.add(memory.id)
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

            target_branch_id = self._resolve_branch_context(session, observation.project_id, None)

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
                BranchMemberRepository(session).set(target_branch_id, memory.id, version.id)
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
                BranchMemberRepository(session).set(target_branch_id, memory_id, version.id)

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
    # Branch operations
    # ------------------------------------------------------------------

    def create_branch(
        self,
        project_id: str,
        name: str,
        source_branch_id: str | None = None,
    ) -> Branch:
        """Create a Branch for a Project.

        The new branch starts from the source branch's knowledge state
        (default: the Project's current branch). Branch names must be unique
        within the Project. Members are shared references to existing Memory
        Versions; no Memory is duplicated.
        """
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            self._ensure_default_branch(session, project_id)
            if BranchRepository(session).get_by_name(project_id, name) is not None:
                raise BranchNameConflictError(name)

            source_id = self._resolve_branch_context(session, project_id, source_branch_id)
            source_members = BranchMemberRepository(session).list_by_branch(source_id)

            branch = Branch(id=new_uuid(), project_id=project_id, name=name, is_default=False)
            BranchRepository(session).create(branch)
            for member in source_members:
                BranchMemberRepository(session).set(
                    branch.id, member.memory_id, member.memory_version_id
                )
            return branch

    def get_branch(self, branch_id: str) -> Branch | None:
        """Retrieve a specific Branch, or None when it does not exist."""
        with self._transaction() as session:
            return BranchRepository(session).get(branch_id)

    def get_branch_by_name(self, project_id: str, name: str) -> Branch | None:
        """Retrieve a Branch by name within a Project, or None."""
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            self._ensure_default_branch(session, project_id)
            return BranchRepository(session).get_by_name(project_id, name)

    def list_branches(self, project_id: str) -> list[Branch]:
        """List all Branches for a Project, ordered by creation."""
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            self._ensure_default_branch(session, project_id)
            return BranchRepository(session).list_by_project(project_id)

    def get_current_branch(self, project_id: str) -> Branch:
        """Return the Project's current Branch (falling back to its default)."""
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            self._ensure_default_branch(session, project_id)
            project = ProjectRepository(session).get(project_id)
            branch = BranchRepository(session).get(project.current_branch_id)
            if branch is not None:
                return branch
            project.current_branch_id = project.default_branch_id
            branch = BranchRepository(session).get(project.default_branch_id)
            if branch is None:
                raise BranchNotFoundError(project.default_branch_id or "(default)")
            return branch

    def switch_branch(self, project_id: str, name: str) -> Branch:
        """Switch the Project's active knowledge context to a Branch by name.

        Branch switching only changes which Branch is used as the default
        retrieval context; it never moves or deletes knowledge.
        """
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            self._ensure_default_branch(session, project_id)
            branch = BranchRepository(session).get_by_name(project_id, name)
            if branch is None:
                raise BranchNotFoundError(name)
            project = ProjectRepository(session).get(project_id)
            project.current_branch_id = branch.id
            return branch

    def get_branch_knowledge(self, branch_id: str) -> list[BranchKnowledge]:
        """Return the knowledge state of a Branch.

        Each item pairs a Memory with the Version that Branch currently
        exposes for it. Shared knowledge appears on every Branch that
        references the same Version.
        """
        with self._transaction() as session:
            branch = BranchRepository(session).get(branch_id)
            if branch is None:
                raise BranchNotFoundError(branch_id)
            results: list[BranchKnowledge] = []
            members = BranchMemberRepository(session).list_by_branch(branch.id)
            members.sort(key=lambda member: (member.created_at, member.memory_id))
            for member in members:
                memory = MemoryRepository(session).get(member.memory_id)
                version = MemoryVersionRepository(session).get(member.memory_version_id)
                if memory is None or version is None:
                    continue
                results.append(BranchKnowledge(memory=memory, version=version))
            return results

    # ------------------------------------------------------------------
    # Snapshot operations
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        project_id: str,
        name: str | None = None,
        message: str | None = None,
        branch_id: str | None = None,
    ) -> Snapshot:
        """Create a Snapshot of a Project's knowledge state.

        Without a Branch context the Snapshot captures the Project's current
        Versions (existing behavior). With ``branch_id`` the Snapshot captures
        that Branch's knowledge state and records the Branch association.
        """
        with self._transaction() as session:
            project = ProjectRepository(session).get(project_id)
            if project is None:
                raise ProjectNotFoundError(project_id)
            if name is not None and SnapshotRepository(session).get_by_name(project_id, name):
                raise SnapshotNameConflictError(name)

            target_branch_id = None
            if branch_id is not None:
                target_branch_id = self._resolve_branch_context(session, project_id, branch_id)

            snapshot = Snapshot(
                id=new_uuid(),
                project_id=project_id,
                name=name,
                branch_id=target_branch_id,
                message=message,
                created_at=utcnow(),
            )
            SnapshotRepository(session).create(snapshot)

            members: list[SnapshotMember] = []
            if target_branch_id is None:
                memories = MemoryRepository(session).list_by_project(project_id)
                for memory in memories:
                    current_version = MemoryVersionRepository(session).highest_version(memory.id)
                    if current_version is not None:
                        members.append(
                            SnapshotMember(
                                snapshot_id=snapshot.id,
                                memory_version_id=current_version.id,
                            )
                        )
            else:
                for member in BranchMemberRepository(session).list_by_branch(target_branch_id):
                    members.append(
                        SnapshotMember(
                            snapshot_id=snapshot.id,
                            memory_version_id=member.memory_version_id,
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

    def get_snapshot_by_name(self, project_id: str, name: str) -> Snapshot | None:
        with self._transaction() as session:
            return SnapshotRepository(session).get_by_name(project_id, name)

    def resolve_snapshot(self, project_id: str, name: str) -> Snapshot:
        """Resolve a Snapshot by its human-readable name within a Project."""
        with self._transaction() as session:
            snapshot = SnapshotRepository(session).get_by_name(project_id, name)
            if snapshot is None:
                raise SnapshotNotFoundError(name)
            _ = snapshot.members
            _ = snapshot.snapshot_relationships
            return snapshot

    def list_snapshots(self, project_id: str, branch_id: str | None = None) -> list[Snapshot]:
        """List all Snapshots for a Project.

        Without ``branch_id`` all Snapshots are returned (existing behavior).
        With ``branch_id`` only Snapshots associated with that Branch are
        returned.
        """
        with self._transaction() as session:
            if branch_id is not None:
                self._resolve_branch_context(session, project_id, branch_id)
            snapshots = SnapshotRepository(session).list_by_project(project_id, branch_id)
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

    # ------------------------------------------------------------------
    # Drift detection operations
    # ------------------------------------------------------------------

    def detect_drift(
        self,
        project_id: str,
        repo_path: str | Path | None = None,
    ) -> DriftReport:
        """Detect whether a Project's knowledge may have drifted.

        The current Git state (branch, HEAD, and working-tree changes) is
        compared against the evidence recorded for each Memory's current
        Version. A dirty tree means the project state differs from the recorded
        reference; affected knowledge is knowledge whose evidence overlaps the
        detected changes. The operation is read-only and never modifies
        knowledge or confidence.
        """
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)

            tree = read_git_tree(repo_path)
            if not tree.is_repo:
                return DriftReport(
                    project_id=project_id,
                    state="clean",
                    reasons=["not in a Git repository — drift cannot be detected"],
                )

            changed = set(tree.changed_files)
            has_reference = False
            affected: list[DriftAffectedKnowledge] = []
            for memory in MemoryRepository(session).list_by_project(project_id):
                current = MemoryVersionRepository(session).highest_version(memory.id)
                if current is None:
                    continue
                for evidence in current.evidence:
                    if evidence.evidence_type != "description":
                        has_reference = True
                    reason = self._evidence_drift_reason(evidence, tree, changed)
                    if reason is None:
                        continue
                    affected.append(
                        DriftAffectedKnowledge(
                            memory_id=memory.id,
                            sequence=current.sequence,
                            content=current.content,
                            reason=reason,
                        )
                    )

            if not has_reference:
                return DriftReport(
                    project_id=project_id,
                    state="clean",
                    reasons=[
                        "no Git context recorded for any knowledge in this project — "
                        "nothing to compare against"
                    ],
                )

            reasons: list[str] = []
            if changed:
                reasons.append(f"{len(changed)} changed artifact(s) in the working tree")
            for knowledge in affected:
                reasons.append(f"memory {knowledge.memory_id} v{knowledge.sequence} may be stale")

            state = "dirty" if changed or affected else "clean"
            return DriftReport(
                project_id=project_id,
                state=state,
                changed_artifacts=sorted(changed),
                affected_knowledge=affected,
                reasons=reasons,
            )

    @staticmethod
    def _evidence_drift_reason(
        evidence: Evidence,
        tree: GitTree,
        changed: set[str],
    ) -> str | None:
        """Return a reason when an Evidence reference no longer matches the tree."""
        if evidence.evidence_type == "commit":
            if tree.head_commit is None or not (
                tree.head_commit.startswith(evidence.ref)
                or evidence.ref.startswith(tree.head_commit)
            ):
                return (
                    f"recorded commit {evidence.ref} does not match current HEAD "
                    f"{tree.head_commit or '(none)'}"
                )
        elif evidence.evidence_type == "branch":
            if tree.current_branch is not None and evidence.ref != tree.current_branch:
                return (
                    f"recorded branch {evidence.ref} does not match current branch "
                    f"{tree.current_branch}"
                )
        else:
            if evidence.ref in changed:
                return f"evidence reference {evidence.ref} has changed in the working tree"
        return None

    # ------------------------------------------------------------------
    # Memory decay operations
    # ------------------------------------------------------------------

    def assess_decay(
        self,
        project_id: str,
        at: datetime | None = None,
        fresh_days: int = DECAY_FRESH_DAYS,
        stale_days: int = DECAY_STALE_DAYS,
    ) -> DecayReport:
        """Assess the freshness (decay) of a Project's current knowledge.

        Each Memory's current Version is scored purely from its ``created_at``
        timestamp relative to the reference time ``at`` (default: now).
        Freshness is a linear score from 1.0 down to 0.0 as the Version ages
        toward ``stale_days``. A Version is "fresh" while its age is below
        ``fresh_days``, "aging" between the thresholds, and "stale" once it
        reaches ``stale_days``. The operation is read-only: it never deletes,
        mutates, or re-verifies knowledge, never changes confidence, and never
        runs drift detection. Results are deterministic for identical inputs.
        """
        if fresh_days <= 0 or stale_days <= 0:
            raise DecayConfigError(
                f"fresh_days and stale_days must be positive, got fresh_days={fresh_days}, "
                f"stale_days={stale_days}"
            )
        if fresh_days > stale_days:
            raise DecayConfigError(
                f"fresh_days must not exceed stale_days, got fresh_days={fresh_days}, "
                f"stale_days={stale_days}"
            )

        now = _naive_utc(at) if at is not None else utcnow()

        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)

            assessments: list[DecayAssessment] = []
            for memory in MemoryRepository(session).list_by_project(project_id):
                current = MemoryVersionRepository(session).highest_version(memory.id)
                if current is None:
                    continue
                created_at = _naive_utc(current.created_at)
                age_days = max(0.0, (now - created_at).total_seconds()) / 86400.0
                freshness = max(0.0, 1.0 - age_days / stale_days)
                if age_days < fresh_days:
                    state = "fresh"
                elif age_days < stale_days:
                    state = "aging"
                else:
                    state = "stale"
                assessments.append(
                    DecayAssessment(
                        memory_id=memory.id,
                        sequence=current.sequence,
                        content=current.content,
                        state=state,
                        freshness=freshness,
                        age_days=age_days,
                        created_at=created_at,
                    )
                )

            return DecayReport(
                project_id=project_id,
                assessments=assessments,
                generated_at=now,
                fresh_days=fresh_days,
                stale_days=stale_days,
            )
