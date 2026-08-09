import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors


@command_errors
def decay(
    project_id: str = typer.Option(..., help="Project id to assess."),
) -> None:
    """Assess the freshness (decay) of a project's knowledge."""
    report = ctx.engine().assess_decay(project_id=project_id)
    _print_report(report)


def _print_report(report) -> None:
    typer.echo(f"Decay [project {report.project_id}]: {len(report.assessments)} assessment(s)")
    typer.echo(f"  thresholds: fresh < {report.fresh_days}d, stale >= {report.stale_days}d")
    for assessment in report.assessments:
        symbol = {"fresh": "+", "aging": "~", "stale": "!"}.get(assessment.state, "?")
        typer.echo(
            f"  [{symbol}] {assessment.state.upper()} memory {assessment.memory_id} "
            f"v{assessment.sequence} — freshness {assessment.freshness:.2f}, "
            f"age {assessment.age_days:.1f}d"
        )
    typer.echo(f"  stale: {report.stale_count}")
