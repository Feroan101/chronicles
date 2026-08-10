import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_project_id

observation_app = typer.Typer(help="Manage project observations.")


@observation_app.command("create")
@command_errors
def create(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    content: str = typer.Option(..., help="Observed information."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    observation = engine.create_observation(project_id=project_uuid, content=content)
    typer.echo(f"Created observation {observation.id}")
    typer.echo(f"  project: {_project_name(engine, project_uuid)}")
    typer.echo(f"  status: {observation.status}")
    typer.echo(f"  content: {observation.content}")


@observation_app.command("list")
@command_errors
def list_observations(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    observations = engine.list_observations(project_id=project_uuid)
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


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id
