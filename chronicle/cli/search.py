import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id


@command_errors
def search_command(
    query: str = typer.Argument(..., help="Keyword query."),
    project: str | None = typer.Option(None, help="Restrict results to a project (name)."),
    project_id: str | None = typer.Option(None, help="Restrict results to a project (UUID)."),
) -> None:
    engine = ctx.engine()
    if project is not None or project_id is not None:
        project_uuid = get_project_id(engine, project=project, project_id=project_id)
    else:
        project_uuid = None
    results = engine.search(query=query, project_id=project_uuid)
    if not results:
        typer.echo("No matches.")
        return
    for result in results:
        memory = result.memory
        version = result.version
        typer.echo(f'Memory "{memory.name}"' if memory.name else f"Memory {memory.id}")
        typer.echo(f"  project: {_project_name(engine, memory.project_id)}")
        typer.echo(f"  type: {memory.type or '-'}")
        typer.echo(f"  current version: {version.sequence} ({version.id})")
        typer.echo(f"  content: {version.content}")
        if version.context:
            typer.echo(f"  context: {version.context}")
        typer.echo("")


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id
