from sqlalchemy import select

from chronicle.models import Snapshot
from chronicle.storage.base import Repository


class SnapshotRepository(Repository):
    def create(self, snapshot: Snapshot) -> Snapshot:
        self._session.add(snapshot)
        return snapshot

    def get(self, snapshot_id: str) -> Snapshot | None:
        return self._session.get(Snapshot, snapshot_id)

    def list_by_project(self, project_id: str, branch_id: str | None = None) -> list[Snapshot]:
        stmt = select(Snapshot).where(Snapshot.project_id == project_id)
        if branch_id is not None:
            stmt = stmt.where(Snapshot.branch_id == branch_id)
        stmt = stmt.order_by(Snapshot.created_at, Snapshot.id)
        return list(self._session.scalars(stmt))
