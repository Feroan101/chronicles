from chronicle.cli.context import CliError
from chronicle.core import ChronicleEngine


def get_project_id(
    engine: ChronicleEngine,
    project: str | None = None,
    project_id: str | None = None,
) -> str:
    """Resolve a Project to its UUID from a name and/or UUID option.

    Exactly one of ``project`` (name) or ``project_id`` (UUID) must be given.
    """
    if project is not None and project_id is not None:
        raise CliError("Provide either --project <name> or --project-id <uuid>, not both.")
    if project is not None:
        return engine.resolve_project(project).id
    if project_id is not None:
        return project_id
    raise CliError("Provide --project <name> or --project-id <uuid>.")


def get_memory_id(
    engine: ChronicleEngine,
    memory: str | None = None,
    memory_id: str | None = None,
    project: str | None = None,
    project_id: str | None = None,
) -> str:
    """Resolve a Memory to its UUID from a name and/or UUID option.

    A name is matched within the given Project when one is supplied,
    otherwise globally (raising when the name is ambiguous).
    """
    if memory is not None and memory_id is not None:
        raise CliError("Provide either --memory <name> or --memory-id <uuid>, not both.")
    if memory_id is not None:
        return memory_id
    if memory is not None:
        scope = None
        if project is not None or project_id is not None:
            scope = get_project_id(engine, project, project_id)
        return engine.resolve_memory(memory, project_id=scope).id
    raise CliError("Provide --memory <name> or --memory-id <uuid>.")


def get_snapshot_id(
    engine: ChronicleEngine,
    project: str | None = None,
    project_id: str | None = None,
    snapshot_name: str | None = None,
    snapshot_id: str | None = None,
) -> str:
    """Resolve a Snapshot to its UUID from a name and/or UUID option.

    Snapshot names are scoped to a Project, so ``project``/``project_id`` is
    required when resolving by name.
    """
    if snapshot_name is not None and snapshot_id is not None:
        raise CliError("Provide either --name <snapshot> or --snapshot-id <uuid>, not both.")
    if snapshot_id is not None:
        return snapshot_id
    if snapshot_name is not None:
        scope = get_project_id(engine, project, project_id)
        return engine.resolve_snapshot(scope, snapshot_name).id
    raise CliError("Provide --name <snapshot> or --snapshot-id <uuid>.")
