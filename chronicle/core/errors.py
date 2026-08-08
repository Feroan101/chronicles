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


class ObservationNotFoundError(ChronicleError):
    def __init__(self, observation_id: str) -> None:
        super().__init__(f"Observation not found: {observation_id}")
        self.observation_id = observation_id


class InvalidObservationActionError(ChronicleError):
    def __init__(self, action: str) -> None:
        super().__init__(
            f"Invalid observation action: {action!r}. "
            "Must be 'create_memory', 'update_memory', or 'discard'."
        )
        self.action = action


class ObservationAlreadyProcessedError(ChronicleError):
    def __init__(self, observation_id: str, status: str) -> None:
        super().__init__(f"Observation {observation_id} is already {status}")
        self.observation_id = observation_id
        self.status = status


class RelationshipNotFoundError(ChronicleError):
    def __init__(self, relationship_id: str) -> None:
        super().__init__(f"Relationship not found: {relationship_id}")
        self.relationship_id = relationship_id


class SelfRelationshipError(ChronicleError):
    def __init__(self) -> None:
        super().__init__("A Relationship cannot connect a Memory to itself")


class CrossProjectRelationshipError(ChronicleError):
    def __init__(self) -> None:
        super().__init__("A Relationship cannot connect Memories from different Projects")
