from sqlalchemy import select

from chronicle.models import Project
from chronicle.storage.base import Repository


class ProjectRepository(Repository):
    def create(self, project: Project) -> Project:
        self._session.add(project)
        return project

    def get(self, project_id: str) -> Project | None:
        return self._session.get(Project, project_id)

    def get_by_name(self, name: str) -> Project | None:
        return self._session.scalars(select(Project).where(Project.name == name)).one_or_none()

    def list_by_name(self, name: str) -> list[Project]:
        return list(
            self._session.scalars(
                select(Project).where(Project.name == name).order_by(Project.created_at, Project.id)
            )
        )

    def list_all(self) -> list[Project]:
        return list(self._session.scalars(select(Project).order_by(Project.created_at, Project.id)))
