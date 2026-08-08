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
    MemoryRead,
    MemorySummaryRead,
    MemoryVersionRead,
    ProjectRead,
    SearchHitRead,
)
from chronicle.core import (
    ChronicleEngine,
    ChronicleError,
    MemoryNotFoundError,
    ProjectNotFoundError,
    SearchQueryError,
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
    ) -> MemoryRead:
        """Store a new memory in a project, with its first version."""
        return _memory(
            self._engine.create_memory(
                project_id=project_id,
                content=content,
                type=type,
                context=context,
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
    ) -> MemoryVersionRead:
        """Append a new version of a memory."""
        return _version(
            self._engine.create_version(
                memory_id=memory_id,
                content=content,
                context=context,
            )
        )

    def search(self, query: str, project_id: str | None = None) -> list[SearchHitRead]:
        """Search project knowledge, returning the current version of matches."""
        return [
            _search_hit(result)
            for result in self._engine.search(query=query, project_id=project_id)
        ]


__all__ = [
    "Chronicle",
    "UNSET",
    "ChronicleError",
    "MemoryNotFoundError",
    "ProjectNotFoundError",
    "SearchQueryError",
    "MemoryRead",
    "MemorySummaryRead",
    "MemoryVersionRead",
    "ProjectRead",
    "SearchHitRead",
]
