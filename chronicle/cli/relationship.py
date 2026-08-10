import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_memory_id, get_project_id

relationship_app = typer.Typer(help="Manage knowledge relationships.")


@relationship_app.command("create")
@command_errors
def create(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    from_memory: str | None = typer.Option(None, help="Source memory name."),
    from_memory_id: str | None = typer.Option(None, help="Source memory UUID."),
    to_memory: str | None = typer.Option(None, help="Target memory name."),
    to_memory_id: str | None = typer.Option(None, help="Target memory UUID."),
    type: str = typer.Option(..., help="Relationship type (e.g. depends_on, caused_by)."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    from_uuid = get_memory_id(
        engine, memory=from_memory, memory_id=from_memory_id, project=project, project_id=project_id
    )
    to_uuid = get_memory_id(
        engine, memory=to_memory, memory_id=to_memory_id, project=project, project_id=project_id
    )
    relationship = engine.create_relationship(
        project_id=project_uuid,
        from_memory_id=from_uuid,
        to_memory_id=to_uuid,
        type=type,
    )
    _print_relationship(engine, relationship, created=True)


@relationship_app.command("list")
@command_errors
def list_relationships(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    relationships = engine.list_relationships(project_id=project_uuid)
    if not relationships:
        typer.echo("No relationships.")
        return
    for rel in relationships:
        _print_relationship(engine, rel)


@relationship_app.command("for-memory")
@command_errors
def for_memory(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
) -> None:
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    relationships = engine.get_relationships_for_memory(memory_id=memory_uuid)
    if not relationships:
        typer.echo("No relationships.")
        return
    for rel in relationships:
        _print_relationship(engine, rel)


@relationship_app.command("remove")
@command_errors
def remove(
    relationship_id: str = typer.Option(..., help="Relationship id to remove."),
) -> None:
    ctx.engine().remove_relationship(relationship_id=relationship_id)
    typer.echo(f"Removed relationship {relationship_id}")


def _memory_label(engine, memory_id: str) -> str:
    memory = engine.get_memory(memory_id)
    return memory.name if memory and memory.name else memory_id


def _print_relationship(engine, rel, created: bool = False) -> None:
    prefix = "Created relationship " if created else ""
    from_label = _memory_label(engine, rel.from_memory_id)
    to_label = _memory_label(engine, rel.to_memory_id)
    typer.echo(f"{prefix}{from_label} -> {to_label}")
    typer.echo(f"  type: {rel.type}")
