from sqlalchemy import select

from chronicle.models import SnapshotRelationship
from chronicle.storage.base import Repository


class SnapshotRelationshipRepository(Repository):
    def create_many(self, relationships: list[SnapshotRelationship]) -> None:
        self._session.add_all(relationships)

    def list_by_snapshot(self, snapshot_id: str) -> list[SnapshotRelationship]:
        return list(
            self._session.scalars(
                select(SnapshotRelationship).where(SnapshotRelationship.snapshot_id == snapshot_id)
            )
        )
