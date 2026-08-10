import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_memory_id

confidence_app = typer.Typer(help="Manage confidence scores for memory versions.")


@confidence_app.command("record")
@command_errors
def record(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    sequence: int = typer.Option(..., help="Version sequence number."),
    score: float = typer.Option(..., help="Confidence score (0.0 to 1.0)."),
    reason: str | None = typer.Option(None, help="Reason for the score."),
) -> None:
    """Record a confidence score for a memory version."""
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    record = engine.record_confidence(
        memory_id=memory_uuid, sequence=sequence, score=score, reason=reason
    )
    label = _memory_label(engine, memory_uuid)
    typer.echo(f'Recorded confidence {record.score} for "{label}" v{sequence}')
    typer.echo(f"  id: {record.id}")


@confidence_app.command("show")
@command_errors
def show(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    sequence: int = typer.Option(..., help="Version sequence number."),
) -> None:
    """Show the current confidence score for a memory version."""
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    score = engine.get_confidence(memory_id=memory_uuid, sequence=sequence)
    if score is None:
        typer.echo("No confidence score recorded for this version.")
        return
    label = _memory_label(engine, memory_uuid)
    typer.echo(f'Confidence for "{label}" v{sequence}')
    typer.echo(f"  score: {score.score}")
    if score.reason:
        typer.echo(f"  reason: {score.reason}")
    typer.echo(f"  recorded_at: {score.recorded_at.isoformat()}")


@confidence_app.command("history")
@command_errors
def history(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    sequence: int = typer.Option(..., help="Version sequence number."),
) -> None:
    """Show the full confidence history for a memory version."""
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    scores = engine.get_confidence_history(memory_id=memory_uuid, sequence=sequence)
    if not scores:
        typer.echo("No confidence history for this version.")
        return
    label = _memory_label(engine, memory_uuid)
    typer.echo(f'Confidence history for "{label}" v{sequence}:')
    for s in scores:
        reason_part = f"  reason: {s.reason}" if s.reason else ""
        typer.echo(f"  {s.recorded_at.isoformat()}  score={s.score}{reason_part}")


def _memory_label(engine, memory_id: str) -> str:
    memory = engine.get_memory(memory_id)
    return memory.name if memory and memory.name else memory_id
