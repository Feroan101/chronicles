import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

confidence_app = typer.Typer(help="Manage confidence scores for memory versions.")


@confidence_app.command("record")
@command_errors
def record(
    memory_id: str = typer.Option(..., help="Memory id."),
    sequence: int = typer.Option(..., help="Version sequence number."),
    score: float = typer.Option(..., help="Confidence score (0.0 to 1.0)."),
    reason: str | None = typer.Option(None, help="Reason for the score."),
) -> None:
    """Record a confidence score for a memory version."""
    record = ctx.engine().record_confidence(
        memory_id=memory_id, sequence=sequence, score=score, reason=reason
    )
    typer.echo(f"Recorded confidence {record.score} for version {sequence}")
    typer.echo(f"  id: {record.id}")
    typer.echo(f"  memory: {memory_id}")
    typer.echo(f"  version: {sequence}")
    if record.reason:
        typer.echo(f"  reason: {record.reason}")


@confidence_app.command("show")
@command_errors
def show(
    memory_id: str = typer.Option(..., help="Memory id."),
    sequence: int = typer.Option(..., help="Version sequence number."),
) -> None:
    """Show the current confidence score for a memory version."""
    score = ctx.engine().get_confidence(memory_id=memory_id, sequence=sequence)
    if score is None:
        typer.echo("No confidence score recorded for this version.")
        return
    typer.echo(f"Confidence for {memory_id} v{sequence}")
    typer.echo(f"  score: {score.score}")
    if score.reason:
        typer.echo(f"  reason: {score.reason}")
    typer.echo(f"  recorded_at: {score.recorded_at.isoformat()}")


@confidence_app.command("history")
@command_errors
def history(
    memory_id: str = typer.Option(..., help="Memory id."),
    sequence: int = typer.Option(..., help="Version sequence number."),
) -> None:
    """Show the full confidence history for a memory version."""
    scores = ctx.engine().get_confidence_history(memory_id=memory_id, sequence=sequence)
    if not scores:
        typer.echo("No confidence history for this version.")
        return
    typer.echo(f"Confidence history for {memory_id} v{sequence}:")
    for s in scores:
        reason_part = f"  reason: {s.reason}" if s.reason else ""
        typer.echo(f"  {s.recorded_at.isoformat()}  score={s.score}{reason_part}")
