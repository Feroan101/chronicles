from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from chronicle.models import Memory
from chronicle.storage.base import Repository


class MemoryRepository(Repository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._load = selectinload(Memory.versions)

    def create(self, memory: Memory) -> Memory:
        self._session.add(memory)
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._session.scalars(
            select(Memory).where(Memory.id == memory_id).options(self._load)
        ).one_or_none()

    def list_by_project(self, project_id: str) -> list[Memory]:
        return list(
            self._session.scalars(
                select(Memory)
                .where(Memory.project_id == project_id)
                .options(self._load)
                .order_by(Memory.created_at, Memory.id)
            )
        )
