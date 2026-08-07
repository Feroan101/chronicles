import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

project_app = typer.Typer(help="Manage projects.")


@project_app.command("create")
@command_errors
def create(
    name: str,
    description: str | None = typer.Option(None, help="Project description."),
) -> None:
    project = ctx.engine().create_project(name=name, description=description)
    typer.echo(f"Created project {project.id}")
    typer.echo(f"  name: {project.name}")
    if project.description:
        typer.echo(f"  description: {project.description}")
