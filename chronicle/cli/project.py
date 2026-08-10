import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id

project_app = typer.Typer(help="Manage projects.")


@project_app.command("create")
@command_errors
def create(
    name: str,
    description: str | None = typer.Option(None, help="Project description."),
) -> None:
    project = ctx.engine().create_project(name=name, description=description)
    typer.echo(f'Created project "{project.name}"')
    typer.echo(f"  id: {project.id}")
    if project.description:
        typer.echo(f"  description: {project.description}")


@project_app.command("list")
@command_errors
def list_projects() -> None:
    projects = ctx.engine().list_projects()
    if not projects:
        typer.echo("No projects.")
        return
    for project in projects:
        description = f"  ({project.description})" if project.description else ""
        typer.echo(f"{project.name}{description}")


@project_app.command("show")
@command_errors
def show(
    name: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    engine = ctx.engine()
    resolved = get_project_id(engine, project=name, project_id=project_id)
    project = engine.get_project(resolved)
    if project is None:
        typer.secho(f"Project not found: {resolved}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.echo(f'Project "{project.name}"')
    typer.echo(f"  id: {project.id}")
    if project.description:
        typer.echo(f"  description: {project.description}")
    typer.echo(f"  created: {project.created_at.isoformat()}")
