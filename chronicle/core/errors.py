class ChronicleError(Exception):
    """Base class for all Chronicle Core errors."""


class ProjectNotFoundError(ChronicleError):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"Project not found: {project_id}")
        self.project_id = project_id


class MemoryNotFoundError(ChronicleError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(f"Memory not found: {memory_id}")
        self.memory_id = memory_id


class SnapshotNotFoundError(ChronicleError):
    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"Snapshot not found: {snapshot_id}")
        self.snapshot_id = snapshot_id


class SelfRelationshipError(ChronicleError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(f"A Relationship cannot connect a Memory to itself: {memory_id}")
        self.memory_id = memory_id


class SearchQueryError(ChronicleError):
    def __init__(self, query: str, detail: str | None = None) -> None:
        if detail is not None:
            super().__init__(f"Invalid search query {query!r}: {detail}")
        else:
            super().__init__(f"Invalid search query: {query}")
        self.query = query


class GitContextError(ChronicleError):
    def __init__(self, field: str | None = None) -> None:
        if field is not None:
            super().__init__(f"Invalid Git context: {field} must not be empty")
        else:
            super().__init__("Invalid Git context: at least one field must be provided")
        self.field = field
