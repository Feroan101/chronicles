import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors


@command_errors
def drift(
    project_id: str = typer.Option(..., help="Project id to check for drift."),
    repo_path: str | None = typer.Option(
        None, help="Path to the Git repository to check (default: current directory)."
    ),
) -> None:
    """Detect whether a project's knowledge may have drifted."""
    report = ctx.engine().detect_drift(project_id=project_id, repo_path=repo_path)
    _print_report(report)


def _print_report(report) -> None:
    state = "DIRTY" if report.dirty else "CLEAN"
    typer.echo(f"Drift [project {report.project_id}]: {state}")
    for reason in report.reasons:
        typer.echo(f"  [~] {reason}")
    for artifact in report.changed_artifacts:
        typer.echo(f"  [!] changed artifact: {artifact}")
    for knowledge in report.affected_knowledge:
        typer.echo(
            f"  [!] affected knowledge: memory {knowledge.memory_id} "
            f"v{knowledge.sequence} — {knowledge.reason}"
        )
