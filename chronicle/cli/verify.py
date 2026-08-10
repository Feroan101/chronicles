import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_memory_id, get_project_id, get_snapshot_id

verify_app = typer.Typer(help="Verify knowledge integrity and traceability.")


@verify_app.command("project")
@command_errors
def verify_project(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    """Verify all knowledge in a project."""
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    report = engine.verify_project(project_id=project_uuid)
    _print_report(report)


@verify_app.command("memory")
@command_errors
def verify_memory(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    """Verify a single memory and its relationships."""
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    report = engine.verify_memory(memory_id=memory_uuid)
    _print_report(report)


@verify_app.command("version")
@command_errors
def verify_version(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    sequence: int = typer.Option(..., help="Version sequence to verify."),
) -> None:
    """Verify a single memory version against its available evidence."""
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    report = engine.verify_version(memory_id=memory_uuid, sequence=sequence)
    _print_report(report)


@verify_app.command("snapshot")
@command_errors
def verify_snapshot(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str | None = typer.Option(None, help="Snapshot name."),
    snapshot_id: str | None = typer.Option(None, help="Snapshot UUID."),
) -> None:
    """Verify a snapshot's captured state against current knowledge."""
    engine = ctx.engine()
    resolved = get_snapshot_id(
        engine,
        project=project,
        project_id=project_id,
        snapshot_name=name,
        snapshot_id=snapshot_id,
    )
    report = engine.verify_snapshot(snapshot_id=resolved)
    _print_report(report)


def _print_report(report) -> None:
    status = "PASSED" if report.passed else "FAILED"
    typer.echo(f"Verification [{report.scope} {report.scope_id}]: {status}")
    for r in report.results:
        symbol = {"verified": "+", "inconclusive": "?", "failed": "!"}.get(r.outcome, "?")
        typer.echo(f"  [{symbol}] {r.check}: {r.message}")
