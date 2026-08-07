from sqlalchemy import func, select

from chronicle.models import MemoryVersion
from chronicle.storage.base import Repository


class MemoryVersionRepository(Repository):
    def create(self, version: MemoryVersion) -> MemoryVersion:
        self._session.add(version)
        return version

    def get(self, version_id: str) -> MemoryVersion | None:
        return self._session.get(MemoryVersion, version_id)

    def list_by_memory(self, memory_id: str) -> list[MemoryVersion]:
        return list(
            self._session.scalars(
                select(MemoryVersion)
                .where(MemoryVersion.memory_id == memory_id)
                .order_by(MemoryVersion.sequence)
            )
        )

    def highest_sequence(self, memory_id: str) -> int:
        highest = self._session.scalar(
            select(func.max(MemoryVersion.sequence)).where(MemoryVersion.memory_id == memory_id)
        )
        return 0 if highest is None else highest
