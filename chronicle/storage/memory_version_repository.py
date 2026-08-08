from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from chronicle.models import MemoryVersion
from chronicle.storage.base import Repository


class MemoryVersionRepository(Repository):
    def create(self, version: MemoryVersion) -> MemoryVersion:
        self._session.add(version)
        return version

    def get(self, version_id: str) -> MemoryVersion | None:
        return self._session.get(MemoryVersion, version_id)

    def get_by_sequence(self, memory_id: str, sequence: int) -> MemoryVersion | None:
        return self._session.scalars(
            select(MemoryVersion)
            .where(MemoryVersion.memory_id == memory_id, MemoryVersion.sequence == sequence)
            .options(selectinload(MemoryVersion.evidence))
        ).one_or_none()

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

    def highest_sequences(self, memory_ids: list[str]) -> dict[str, int]:
        """Return the highest sequence for each Memory id."""
        if not memory_ids:
            return {}
        rows = self._session.execute(
            select(MemoryVersion.memory_id, func.max(MemoryVersion.sequence))
            .where(MemoryVersion.memory_id.in_(memory_ids))
            .group_by(MemoryVersion.memory_id)
        )
        return {memory_id: sequence for memory_id, sequence in rows}

    def highest_version(self, memory_id: str) -> MemoryVersion | None:
        """Return the Current Version (highest sequence) for a Memory."""
        return self._session.scalars(
            select(MemoryVersion)
            .where(MemoryVersion.memory_id == memory_id)
            .order_by(MemoryVersion.sequence.desc())
            .limit(1)
        ).one_or_none()
