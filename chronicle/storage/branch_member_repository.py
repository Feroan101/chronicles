from sqlalchemy import select

from chronicle.models import BranchMember
from chronicle.storage.base import Repository


class BranchMemberRepository(Repository):
    def create(self, member: BranchMember) -> BranchMember:
        self._session.add(member)
        return member

    def get(self, branch_id: str, memory_id: str) -> BranchMember | None:
        return self._session.get(BranchMember, (branch_id, memory_id))

    def set(self, branch_id: str, memory_id: str, memory_version_id: str) -> BranchMember:
        """Set the Version visible for a Memory on a Branch.

        Updates the existing membership if present, otherwise creates it.
        """
        member = self._session.get(BranchMember, (branch_id, memory_id))
        if member is None:
            member = BranchMember(
                branch_id=branch_id,
                memory_id=memory_id,
                memory_version_id=memory_version_id,
            )
            self._session.add(member)
        else:
            member.memory_version_id = memory_version_id
        return member

    def list_by_branch(self, branch_id: str) -> list[BranchMember]:
        return list(
            self._session.scalars(select(BranchMember).where(BranchMember.branch_id == branch_id))
        )

    def list_by_memory(self, memory_id: str) -> list[BranchMember]:
        return list(
            self._session.scalars(select(BranchMember).where(BranchMember.memory_id == memory_id))
        )
