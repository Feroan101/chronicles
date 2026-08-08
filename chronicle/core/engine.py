from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from chronicle.core.errors import (
    MemoryNotFoundError,
    ProjectNotFoundError,
    SearchQueryError,
)
from chronicle.core.git import GitContext
from chronicle.models import Evidence, Memory, MemoryVersion, Project
from chronicle.storage import (
    EvidenceRepository,
    MemoryRepository,
    MemoryVersionRepository,
    ProjectRepository,
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
