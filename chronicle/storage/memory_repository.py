from sqlalchemy import Column, MetaData, Table, Text, select, text
from sqlalchemy.orm import Session, selectinload

from chronicle.models import Memory, MemoryVersion
from chronicle.storage.base import Repository

_SEARCH_INDEX = Table(
    "search_index",
    MetaData(),
    Column("memory_id", Text),
    Column("memory_version_id", Text),
    Column("content", Text),
)

_BM25 = text("bm25(search_index)")


def _fts_query(query: str) -> str:
    """Express a plain keyword query as a safe FTS5 query.

    Each keyword is quoted so punctuation and FTS5 operators (AND, OR, NOT)
    are treated as literal text, and keywords are combined with AND.
    """
    return " AND ".join(f'"{term}"' for term in query.split())


class MemoryRepository(Repository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._load = selectinload(Memory.versions).selectinload(MemoryVersion.evidence)

    def create(self, memory: Memory) -> Memory:
        self._session.add(memory)
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._session.scalars(
            select(Memory).where(Memory.id == memory_id).options(self._load)
        ).one_or_none()

    def get_by_name(self, project_id: str, name: str) -> Memory | None:
        return self._session.scalars(
            select(Memory)
            .where(Memory.project_id == project_id, Memory.name == name)
            .options(self._load)
        ).one_or_none()

    def list_by_name(self, name: str) -> list[Memory]:
        """Return Memories sharing a name across all projects."""
        return list(
            self._session.scalars(select(Memory).where(Memory.name == name).options(self._load))
        )

    def list_by_project(self, project_id: str) -> list[Memory]:
        return list(
            self._session.scalars(
                select(Memory)
                .where(Memory.project_id == project_id)
                .options(self._load)
                .order_by(Memory.created_at, Memory.id)
            )
        )

    def search(
        self, query: str, project_id: str | None = None
    ) -> list[tuple[Memory, MemoryVersion, float]]:
        """Return Memory and Memory Version rows matching the query.

        The FTS5 index ranks matches using bm25 (lower is better). All
        matching rows are returned, including historical Versions; current
        version selection is a Chronicle Core concern.
        """
        stmt = (
            select(Memory, MemoryVersion, _BM25)
            .join_from(
                _SEARCH_INDEX,
                MemoryVersion,
                MemoryVersion.id == _SEARCH_INDEX.c.memory_version_id,
            )
            .join(Memory, Memory.id == MemoryVersion.memory_id)
            .where(_SEARCH_INDEX.c.content.match(_fts_query(query)))
            .order_by(_BM25, Memory.id, MemoryVersion.sequence)
        )
        if project_id is not None:
            stmt = stmt.where(Memory.project_id == project_id)
        return list(self._session.execute(stmt).all())
