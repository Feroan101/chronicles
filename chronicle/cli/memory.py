import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

memory_app = typer.Typer(help="Manage memories.")


@memory_app.command("create")
@command_errors
def create(
    project_id: str = typer.Option(..., help="Owning project id."),
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
    git_ctx = None
    if any([git_branch, git_commit, git_description]):
        from chronicle.core.git import GitContext

        git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
    memory = ctx.engine().create_memory(
        project_id=project_id,
        content=content,
        type=type,
        context=context,
        git_context=git_ctx,
        branch_id=branch,
    )
    current = memory.versions[-1]
    typer.echo(f"Created memory {memory.id}")
    typer.echo(f"  project: {memory.project_id}")
    typer.echo(f"  type: {memory.type or '-'}")
    typer.echo(f"  current version: {current.sequence} ({current.id})")


@memory_app.command("list")
@command_errors
def list_memories(
    project_id: str = typer.Option(..., help="Project id to list memories for."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the project's current branch."
    ),
) -> None:
    memories = ctx.engine().list_memories(project_id=project_id, branch_id=branch)
    if not memories:
        typer.echo("No memories.")
        return
    for memory in memories:
        current = memory.versions[-1]
        typer.echo(f"{memory.id}  {memory.type or '-'}  seq {current.sequence}")


@memory_app.command("show")
@command_errors
def show(memory_id: str = typer.Option(..., help="Memory id to display.")) -> None:
    memory = ctx.engine().get_memory(memory_id)
    if memory is None:
        typer.secho(f"Memory not found: {memory_id}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)
    current = memory.versions[-1]
    typer.echo(f"Memory {memory.id}")
    typer.echo(f"  project: {memory.project_id}")
    typer.echo(f"  type: {memory.type or '-'}")
    typer.echo(f"  created: {memory.created_at.isoformat()}")
    typer.echo(f"Current version (sequence {current.sequence})")
    typer.echo(f"  content: {current.content}")
    if current.context:
        typer.echo(f"  context: {current.context}")
