import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id

branch_app = typer.Typer(help="Manage project branches.")


@branch_app.command("create")
@command_errors
def create(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str = typer.Option(..., help="Branch name (must be a valid identifier)."),
    source: str | None = typer.Option(
        None, "--source", help="Source branch id to fork from. Defaults to current."
    ),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    branch = engine.create_branch(project_id=project_uuid, name=name, source_branch_id=source)
    typer.echo(f"Created branch {branch.name}")
    typer.echo(f"  id: {branch.id}")
    typer.echo(f"  project: {_project_name(engine, project_uuid)}")
    typer.echo(f"  default: {branch.is_default}")


@branch_app.command("list")
@command_errors
def list_branches(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    branches = engine.list_branches(project_id=project_uuid)
    if not branches:
        typer.echo("No branches.")
        return
    for branch in branches:
        default = " (default)" if branch.is_default else ""
        typer.echo(f"{branch.name}  {branch.id}{default}")


@branch_app.command("switch")
@command_errors
def switch(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str = typer.Option(..., help="Branch name to activate."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    branch = engine.switch_branch(project_id=project_uuid, name=name)
    typer.echo(f"Switched {_project_name(engine, project_uuid)} to branch {branch.name}")


@branch_app.command("current")
@command_errors
def current(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    branch = engine.get_current_branch(project_id=project_uuid)
    default = " (default)" if branch.is_default else ""
    typer.echo(f"{branch.name}  {branch.id}{default}")


@branch_app.command("knowledge")
@command_errors
def knowledge(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str | None = typer.Option(None, help="Branch name."),
    branch_id: str | None = typer.Option(None, help="Branch UUID."),
) -> None:
    engine = ctx.engine()
    if name is not None and branch_id is not None:
        typer.secho("Provide either --name <branch> or --branch-id <uuid>, not both.", err=True)
        raise typer.Exit(code=1)
    if branch_id is None:
        project_uuid = get_project_id(engine, project=project, project_id=project_id)
        if name is None:
            branch = engine.get_current_branch(project_id=project_uuid)
        else:
            branch = engine.get_branch_by_name(project_id=project_uuid, name=name)
            if branch is None:
                typer.secho(f"Branch not found: {name}", err=True, fg=typer.colors.RED)
                raise typer.Exit(code=1)
        branch_id = branch.id
    items = engine.get_branch_knowledge(branch_id=branch_id)
    if not items:
        typer.echo("No knowledge yet.")
        return
    for item in items:
        memory = item.memory
        version = item.version
        label = memory.name or memory.id
        typer.echo(f"{label}  seq {version.sequence}  {memory.type or '-'}")
        typer.echo(f"  {version.content}")


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id
