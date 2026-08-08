import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

observation_app = typer.Typer(help="Manage project observations.")


@observation_app.command("create")
@command_errors
def create(
    project_id: str = typer.Option(..., help="Owning project id."),
    content: str = typer.Option(..., help="Observed information."),
) -> None:
    observation = ctx.engine().create_observation(project_id=project_id, content=content)
    typer.echo(f"Created observation {observation.id}")
    typer.echo(f"  project: {observation.project_id}")
    typer.echo(f"  status: {observation.status}")
    typer.echo(f"  content: {observation.content}")


@observation_app.command("list")
@command_errors
def list_observations(
    project_id: str = typer.Option(..., help="Project id to list observations for."),
) -> None:
    observations = ctx.engine().list_observations(project_id=project_id)
    if not observations:
        typer.echo("No observations.")
        return
    for obs in observations:
        typer.echo(f"{obs.id}  {obs.status}  {obs.content[:60]}")


@observation_app.command("process")
@command_errors
def process(
    observation_id: str = typer.Option(..., help="Observation id to process."),
    action: str = typer.Option(..., help="Action: create_memory, update_memory, discard."),
    memory_id: str | None = typer.Option(None, help="Memory id (required for update_memory)."),
) -> None:
    observation = ctx.engine().process_observation(
        observation_id=observation_id,
        action=action,
        memory_id=memory_id,
    )
    typer.echo(f"Processed observation {observation.id}")
    typer.echo(f"  status: {observation.status}")
