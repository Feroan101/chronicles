from sqlalchemy import select

from chronicle.models import ConfidenceScore
from chronicle.storage.base import Repository


class ConfidenceRepository(Repository):
    def create(self, score: ConfidenceScore) -> ConfidenceScore:
        self._session.add(score)
        return score

    def list_by_version(self, memory_version_id: str) -> list[ConfidenceScore]:
        return list(
            self._session.scalars(
                select(ConfidenceScore)
                .where(ConfidenceScore.memory_version_id == memory_version_id)
                .order_by(ConfidenceScore.recorded_at, ConfidenceScore.id)
            )
        )

    def latest_by_version(self, memory_version_id: str) -> ConfidenceScore | None:
        stmt = (
            select(ConfidenceScore)
            .where(ConfidenceScore.memory_version_id == memory_version_id)
            .order_by(ConfidenceScore.recorded_at.desc(), ConfidenceScore.id.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).one_or_none()
