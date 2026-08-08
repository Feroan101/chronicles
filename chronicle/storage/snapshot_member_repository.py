from sqlalchemy import select

from chronicle.models import SnapshotMember
from chronicle.storage.base import Repository


class SnapshotMemberRepository(Repository):
    def create_many(self, members: list[SnapshotMember]) -> None:
        self._session.add_all(members)

    def list_by_snapshot(self, snapshot_id: str) -> list[SnapshotMember]:
        return list(
            self._session.scalars(
                select(SnapshotMember).where(SnapshotMember.snapshot_id == snapshot_id)
            )
        )
