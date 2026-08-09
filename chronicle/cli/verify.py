import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

verify_app = typer.Typer(help="Verify knowledge integrity and traceability.")


@verify_app.command("project")
@command_errors
def verify_project(
    project_id: str = typer.Option(..., help="Project id to verify."),
) -> None:
    """Verify all knowledge in a project."""
    report = ctx.engine().verify_project(project_id=project_id)
    _print_report(report)


@verify_app.command("memory")
@command_errors
def verify_memory(
    memory_id: str = typer.Option(..., help="Memory id to verify."),
) -> None:
    """Verify a single memory and its relationships."""
    report = ctx.engine().verify_memory(memory_id=memory_id)
    _print_report(report)


@verify_app.command("version")
@command_errors
def verify_version(
    memory_id: str = typer.Option(..., help="Memory id of the version to verify."),
    sequence: int = typer.Option(..., help="Version sequence to verify."),
) -> None:
    """Verify a single memory version against its available evidence."""
    report = ctx.engine().verify_version(memory_id=memory_id, sequence=sequence)
    _print_report(report)


@verify_app.command("snapshot")
@command_errors
def verify_snapshot(
    snapshot_id: str = typer.Option(..., help="Snapshot id to verify."),
) -> None:
    """Verify a snapshot's captured state against current knowledge."""
    report = ctx.engine().verify_snapshot(snapshot_id=snapshot_id)
    _print_report(report)


def _print_report(report) -> None:
    status = "PASSED" if report.passed else "FAILED"
    typer.echo(f"Verification [{report.scope} {report.scope_id}]: {status}")
    for r in report.results:
        symbol = {"verified": "+", "inconclusive": "?", "failed": "!"}.get(r.outcome, "?")
        typer.echo(f"  [{symbol}] {r.check}: {r.message}")
