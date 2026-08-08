import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors


@command_errors
def search_command(
    query: str = typer.Argument(..., help="Keyword query."),
    project_id: str | None = typer.Option(None, help="Restrict results to a project."),
) -> None:
    results = ctx.engine().search(query=query, project_id=project_id)
    if not results:
        typer.echo("No matches.")
        return
    for result in results:
        memory = result.memory
        version = result.version
        typer.echo(f"Memory {memory.id}")
        typer.echo(f"  project: {memory.project_id}")
        typer.echo(f"  type: {memory.type or '-'}")
        typer.echo(f"  current version: {version.sequence} ({version.id})")
        typer.echo(f"  content: {version.content}")
        if version.context:
            typer.echo(f"  context: {version.context}")
        typer.echo("")
