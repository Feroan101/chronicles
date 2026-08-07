from chronicle.models import Project
from chronicle.storage.base import Repository


class ProjectRepository(Repository):
    def create(self, project: Project) -> Project:
        self._session.add(project)
        return project

    def get(self, project_id: str) -> Project | None:
        return self._session.get(Project, project_id)
