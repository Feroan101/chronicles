from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from chronicle.core.errors import MemoryNotFoundError, ProjectNotFoundError
from chronicle.models import Memory, MemoryVersion, Project
from chronicle.storage import (
    MemoryRepository,
    MemoryVersionRepository,
    ProjectRepository,
)
from chronicle.utils.ids import new_uuid

_UNSET = object()


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
    ) -> Memory:
        with self._transaction() as session:
            if ProjectRepository(session).get(project_id) is None:
                raise ProjectNotFoundError(project_id)
            memory = Memory(id=new_uuid(), project_id=project_id, type=type)
            MemoryRepository(session).create(memory)
            MemoryVersionRepository(session).create(
                MemoryVersion(
                    id=new_uuid(),
                    memory_id=memory.id,
                    sequence=1,
                    content=content,
                    context=context,
                )
            )
            session.flush()
            list(memory.versions)
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
    ) -> MemoryVersion:
        with self._transaction() as session:
            if MemoryRepository(session).get(memory_id) is None:
                raise MemoryNotFoundError(memory_id)
            next_sequence = MemoryVersionRepository(session).highest_sequence(memory_id) + 1
            return MemoryVersionRepository(session).create(
                MemoryVersion(
                    id=new_uuid(),
                    memory_id=memory_id,
                    sequence=next_sequence,
                    content=content,
                    context=context,
                )
            )

    def list_memories(self, project_id: str) -> list[Memory]:
        with self._transaction() as session:
            return MemoryRepository(session).list_by_project(project_id)
