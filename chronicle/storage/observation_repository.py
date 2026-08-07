from sqlalchemy import select

from chronicle.models import Observation
from chronicle.storage.base import Repository


class ObservationRepository(Repository):
    def create(self, observation: Observation) -> Observation:
        self._session.add(observation)
        return observation

    def get(self, observation_id: str) -> Observation | None:
        return self._session.get(Observation, observation_id)

    def list_by_project(self, project_id: str) -> list[Observation]:
        return list(
            self._session.scalars(
                select(Observation)
                .where(Observation.project_id == project_id)
                .order_by(Observation.created_at, Observation.id)
            )
        )
