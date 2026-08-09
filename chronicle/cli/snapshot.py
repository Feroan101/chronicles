import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

snapshot_app = typer.Typer(help="Manage project snapshots.")


@snapshot_app.command("create")
@command_errors
def create(
    project_id: str = typer.Option(..., help="Project id to snapshot."),
    message: str | None = typer.Option(None, help="Optional snapshot message."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    snapshot = ctx.engine().create_snapshot(
        project_id=project_id, message=message, branch_id=branch
    )
    typer.echo(f"Created snapshot {snapshot.id}")
    typer.echo(f"  project: {snapshot.project_id}")
    typer.echo(f"  branch: {snapshot.branch_id or '-'}")
    typer.echo(f"  message: {snapshot.message or '(none)'}")
    typer.echo(f"  members: {len(snapshot.members)}")
    typer.echo(f"  relationships: {len(snapshot.snapshot_relationships)}")


@snapshot_app.command("list")
@command_errors
def list_snapshots(
    project_id: str = typer.Option(..., help="Project id to list snapshots for."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    engine = ctx.engine()
    if branch:
        snapshots = engine.list_snapshots(project_id=project_id, branch_id=branch)
    else:
        snapshots = engine.list_snapshots(project_id=project_id)
    if not snapshots:
        typer.echo("No snapshots.")
        return
    for snapshot in snapshots:
        msg = snapshot.message or "(no message)"
        typer.echo(f"{snapshot.id}  {msg}  {len(snapshot.members)} members")


@snapshot_app.command("get")
@command_errors
def get(
    snapshot_id: str = typer.Option(..., help="Snapshot id to retrieve."),
) -> None:
    snapshot = ctx.engine().get_snapshot(snapshot_id=snapshot_id)
    if snapshot is None:
        typer.echo(f"Snapshot not found: {snapshot_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Snapshot {snapshot.id}")
    typer.echo(f"  project: {snapshot.project_id}")
    typer.echo(f"  message: {snapshot.message or '(none)'}")
    typer.echo(f"  created: {snapshot.created_at}")
    typer.echo(f"  members: {len(snapshot.members)}")
    typer.echo(f"  relationships: {len(snapshot.snapshot_relationships)}")
