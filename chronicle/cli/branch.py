import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

branch_app = typer.Typer(help="Manage project branches.")


@branch_app.command("create")
@command_errors
def create(
    project_id: str = typer.Option(..., help="Owning project id."),
    name: str = typer.Option(..., help="Branch name (must be a valid identifier)."),
    source: str | None = typer.Option(
        None, "--source", help="Source branch id to fork from. Defaults to current."
    ),
) -> None:
    branch = ctx.engine().create_branch(project_id=project_id, name=name, source_branch_id=source)
    typer.echo(f"Created branch {branch.name} ({branch.id})")
    typer.echo(f"  project: {branch.project_id}")
    typer.echo(f"  default: {branch.is_default}")


@branch_app.command("list")
@command_errors
def list_branches(
    project_id: str = typer.Option(..., help="Project id to list branches for."),
) -> None:
    branches = ctx.engine().list_branches(project_id=project_id)
    if not branches:
        typer.echo("No branches.")
        return
    for branch in branches:
        default = " (default)" if branch.is_default else ""
        typer.echo(f"{branch.name}  {branch.id}{default}")


@branch_app.command("switch")
@command_errors
def switch(
    project_id: str = typer.Option(..., help="Project id."),
    name: str = typer.Option(..., help="Branch name to activate."),
) -> None:
    branch = ctx.engine().switch_branch(project_id=project_id, name=name)
    typer.echo(f"Switched {project_id} to branch {branch.name} ({branch.id})")


@branch_app.command("current")
@command_errors
def current(
    project_id: str = typer.Option(..., help="Project id."),
) -> None:
    branch = ctx.engine().get_current_branch(project_id=project_id)
    default = " (default)" if branch.is_default else ""
    typer.echo(f"{branch.name}  {branch.id}{default}")


@branch_app.command("knowledge")
@command_errors
def knowledge(
    branch_id: str = typer.Option(..., help="Branch id."),
) -> None:
    items = ctx.engine().get_branch_knowledge(branch_id=branch_id)
    if not items:
        typer.echo("No knowledge yet.")
        return
    for item in items:
        memory = item.memory
        version = item.version
        typer.echo(f"{memory.id}  seq {version.sequence}  {memory.type or '-'}")
        typer.echo(f"  {version.content}")
