import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id, get_snapshot_id

snapshot_app = typer.Typer(help="Manage project snapshots.")


@snapshot_app.command("create")
@command_errors
def create(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str | None = typer.Option(None, help="Snapshot name (human-readable)."),
    message: str | None = typer.Option(None, help="Optional snapshot message."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    snapshot = engine.create_snapshot(
        project_id=project_uuid, name=name, message=message, branch_id=branch
    )
    typer.echo(f'Created snapshot "{name}"' if name else f"Created snapshot {snapshot.id}")
    typer.echo(f"  id: {snapshot.id}")
    typer.echo(f"  project: {_project_name(engine, project_uuid)}")
    typer.echo(f"  message: {snapshot.message or '(none)'}")
    typer.echo(f"  members: {len(snapshot.members)}")
    typer.echo(f"  relationships: {len(snapshot.snapshot_relationships)}")


@snapshot_app.command("list")
@command_errors
def list_snapshots(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    if branch:
        snapshots = engine.list_snapshots(project_id=project_uuid, branch_id=branch)
    else:
        snapshots = engine.list_snapshots(project_id=project_uuid)
    if not snapshots:
        typer.echo("No snapshots.")
        return
    for snapshot in snapshots:
        label = snapshot.name or snapshot.id
        msg = snapshot.message or "(no message)"
        typer.echo(f"{label}  {msg}  {len(snapshot.members)} members")


@snapshot_app.command("get")
@command_errors
def get(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str | None = typer.Option(None, help="Snapshot name."),
    snapshot_id: str | None = typer.Option(None, help="Snapshot UUID."),
) -> None:
    engine = ctx.engine()
    resolved = get_snapshot_id(
        engine,
        project=project,
        project_id=project_id,
        snapshot_name=name,
        snapshot_id=snapshot_id,
    )
    snapshot = engine.get_snapshot(snapshot_id=resolved)
    if snapshot is None:
        typer.echo(f"Snapshot not found: {resolved}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f'Snapshot "{snapshot.name}"' if snapshot.name else f"Snapshot {snapshot.id}")
    typer.echo(f"  id: {snapshot.id}")
    typer.echo(f"  project: {_project_name(engine, snapshot.project_id)}")
    typer.echo(f"  message: {snapshot.message or '(none)'}")
    typer.echo(f"  created: {snapshot.created_at}")
    typer.echo(f"  members: {len(snapshot.members)}")
    typer.echo(f"  relationships: {len(snapshot.snapshot_relationships)}")


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id
