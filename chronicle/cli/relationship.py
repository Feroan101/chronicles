import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

relationship_app = typer.Typer(help="Manage knowledge relationships.")


@relationship_app.command("create")
@command_errors
def create(
    project_id: str = typer.Option(..., help="Owning project id."),
    from_memory_id: str = typer.Option(..., help="Source memory id."),
    to_memory_id: str = typer.Option(..., help="Target memory id."),
    type: str = typer.Option(..., help="Relationship type (e.g. caused_by, resolved_by)."),
) -> None:
    relationship = ctx.engine().create_relationship(
        project_id=project_id,
        from_memory_id=from_memory_id,
        to_memory_id=to_memory_id,
        type=type,
    )
    typer.echo(f"Created relationship {relationship.id}")
    typer.echo(f"  project: {relationship.project_id}")
    typer.echo(f"  type: {relationship.type}")
    typer.echo(f"  from: {relationship.from_memory_id}")
    typer.echo(f"  to: {relationship.to_memory_id}")


@relationship_app.command("list")
@command_errors
def list_relationships(
    project_id: str = typer.Option(..., help="Project id to list relationships for."),
) -> None:
    relationships = ctx.engine().list_relationships(project_id=project_id)
    if not relationships:
        typer.echo("No relationships.")
        return
    for rel in relationships:
        typer.echo(f"{rel.id}  {rel.type}  {rel.from_memory_id} -> {rel.to_memory_id}")


@relationship_app.command("for-memory")
@command_errors
def for_memory(
    memory_id: str = typer.Option(..., help="Memory id to get relationships for."),
) -> None:
    relationships = ctx.engine().get_relationships_for_memory(memory_id=memory_id)
    if not relationships:
        typer.echo("No relationships.")
        return
    for rel in relationships:
        typer.echo(f"{rel.id}  {rel.type}  {rel.from_memory_id} -> {rel.to_memory_id}")


@relationship_app.command("remove")
@command_errors
def remove(
    relationship_id: str = typer.Option(..., help="Relationship id to remove."),
) -> None:
    ctx.engine().remove_relationship(relationship_id=relationship_id)
    typer.echo(f"Removed relationship {relationship_id}")
