import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id


@command_errors
def drift(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    repo_path: str | None = typer.Option(
        None, help="Path to the Git repository to check (default: current directory)."
    ),
) -> None:
    """Detect whether a project's knowledge may have drifted."""
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    report = engine.detect_drift(project_id=project_uuid, repo_path=repo_path)
    _print_report(engine, report, _project_name(engine, project_uuid))


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id


def _memory_label(engine, memory_id: str) -> str:
    memory = engine.get_memory(memory_id)
    return memory.name if memory and memory.name else memory_id


def _print_report(engine, report, project_name: str) -> None:
    state = "DIRTY" if report.dirty else "CLEAN"
    typer.echo(f"Drift · {project_name}: {state}")
    for reason in report.reasons:
        typer.echo(f"  [~] {reason}")
    for artifact in report.changed_artifacts:
        typer.echo(f"  [!] changed artifact: {artifact}")
    for knowledge in report.affected_knowledge:
        label = _memory_label(engine, knowledge.memory_id)
        typer.echo(
            f"  [!] affected knowledge: memory {label} v{knowledge.sequence} — {knowledge.reason}"
        )
