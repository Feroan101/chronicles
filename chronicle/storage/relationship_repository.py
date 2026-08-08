from sqlalchemy import select

from chronicle.models import Relationship
from chronicle.storage.base import Repository


class RelationshipRepository(Repository):
    def create(self, relationship: Relationship) -> Relationship:
        self._session.add(relationship)
        return relationship

    def get(self, relationship_id: str) -> Relationship | None:
        return self._session.get(Relationship, relationship_id)

    def list_by_project(self, project_id: str) -> list[Relationship]:
        return list(
            self._session.scalars(
                select(Relationship)
                .where(Relationship.project_id == project_id)
                .order_by(Relationship.created_at, Relationship.id)
            )
        )

    def list_by_memory(self, memory_id: str) -> list[Relationship]:
        return list(
            self._session.scalars(
                select(Relationship)
                .where(
                    (Relationship.from_memory_id == memory_id)
                    | (Relationship.to_memory_id == memory_id)
                )
                .order_by(Relationship.created_at, Relationship.id)
            )
        )

    def delete(self, relationship_id: str) -> bool:
        relationship = self.get(relationship_id)
        if relationship is None:
            return False
        self._session.delete(relationship)
        return True
