import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id


@command_errors
def decay(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    """Assess the freshness (decay) of a project's knowledge."""
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    report = engine.assess_decay(project_id=project_uuid)
    _print_report(engine, report, _project_name(engine, project_uuid))


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id


def _memory_label(engine, memory_id: str) -> str:
    memory = engine.get_memory(memory_id)
    return memory.name if memory and memory.name else memory_id


def _print_report(engine, report, project_name: str) -> None:
    typer.echo(f"Decay · {project_name}: {len(report.assessments)} assessment(s)")
    typer.echo(f"  thresholds: fresh < {report.fresh_days}d, stale >= {report.stale_days}d")
    for assessment in report.assessments:
        symbol = {"fresh": "+", "aging": "~", "stale": "!"}.get(assessment.state, "?")
        label = _memory_label(engine, assessment.memory_id)
        typer.echo(
            f"  [{symbol}] {assessment.state.upper()} memory {label} "
            f"v{assessment.sequence} — freshness {assessment.freshness:.2f}, "
            f"age {assessment.age_days:.1f}d"
        )
    typer.echo(f"  stale: {report.stale_count}")
