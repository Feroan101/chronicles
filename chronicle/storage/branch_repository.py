from sqlalchemy import select

from chronicle.models import Branch
from chronicle.storage.base import Repository


class BranchRepository(Repository):
    def create(self, branch: Branch) -> Branch:
        self._session.add(branch)
        return branch

    def get(self, branch_id: str) -> Branch | None:
        return self._session.get(Branch, branch_id)

    def get_by_name(self, project_id: str, name: str) -> Branch | None:
        return self._session.scalars(
            select(Branch).where(Branch.project_id == project_id, Branch.name == name)
        ).one_or_none()

    def list_by_project(self, project_id: str) -> list[Branch]:
        return list(
            self._session.scalars(
                select(Branch)
                .where(Branch.project_id == project_id)
                .order_by(Branch.created_at, Branch.id)
            )
        )
