import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_memory_id, get_project_id

memory_app = typer.Typer(help="Manage memories.")


@memory_app.command("create")
@command_errors
def create(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    name: str | None = typer.Option(None, help="Memory name (human-readable)."),
    content: str = typer.Option(..., help="Memory content."),
    type: str | None = typer.Option(None, help="Memory type (e.g. fact, decision)."),
    context: str | None = typer.Option(None, help="Where the knowledge applies."),
    git_branch: str | None = typer.Option(None, help="Git branch name."),
    git_commit: str | None = typer.Option(None, help="Git commit hash."),
    git_description: str | None = typer.Option(None, help="Git change description."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    git_ctx = None
    if any([git_branch, git_commit, git_description]):
        from chronicle.core.git import GitContext

        git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
    memory = engine.create_memory(
        project_id=project_uuid,
        name=name,
        content=content,
        type=type,
        context=context,
        git_context=git_ctx,
        branch_id=branch,
    )
    current = memory.versions[-1]
    typer.echo(f'Created memory "{name}"' if name else f"Created memory {memory.id}")
    typer.echo(f"  project: {_project_name(engine, memory.project_id)}")
    typer.echo(f"  type: {memory.type or '-'}")
    typer.echo(f"  current version: {current.sequence}")
    if name:
        typer.echo(f"  id: {memory.id}")


@memory_app.command("list")
@command_errors
def list_memories(
    project: str | None = typer.Option(None, help="Project name."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    engine = ctx.engine()
    project_uuid = get_project_id(engine, project=project, project_id=project_id)
    memories = engine.list_memories(project_id=project_uuid, branch_id=branch)
    if not memories:
        typer.echo("No memories.")
        return
    for memory in memories:
        current = memory.versions[-1]
        label = memory.name or memory.id
        typer.echo(f"{label}  {memory.type or '-'}  seq {current.sequence}")


@memory_app.command("show")
@command_errors
def show(
    name: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
) -> None:
    engine = ctx.engine()
    resolved = get_memory_id(
        engine, memory=name, memory_id=memory_id, project=project, project_id=project_id
    )
    memory = engine.get_memory(resolved)
    if memory is None:
        typer.secho(f"Memory not found: {resolved}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)
    current = memory.versions[-1]
    typer.echo(f'Memory "{memory.name}"' if memory.name else f"Memory {memory.id}")
    typer.echo(f"  project: {_project_name(engine, memory.project_id)}")
    typer.echo(f"  type: {memory.type or '-'}")
    typer.echo(f"  created: {memory.created_at.isoformat()}")
    typer.echo(f"Current version (sequence {current.sequence})")
    typer.echo(f"  content: {current.content}")
    if current.context:
        typer.echo(f"  context: {current.context}")


def _project_name(engine, project_id: str) -> str:
    project = engine.get_project(project_id)
    return project.name if project is not None else project_id
