from sqlalchemy import select

from chronicle.models import Evidence
from chronicle.storage.base import Repository


class EvidenceRepository(Repository):
    def create(self, evidence: Evidence) -> Evidence:
        self._session.add(evidence)
        return evidence

    def list_by_version(self, memory_version_id: str) -> list[Evidence]:
        return list(
            self._session.scalars(
                select(Evidence)
                .where(Evidence.memory_version_id == memory_version_id)
                .order_by(Evidence.recorded_at, Evidence.id)
            )
        )
