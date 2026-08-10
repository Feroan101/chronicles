import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors
from chronicle.cli.resolvers import get_memory_id

version_app = typer.Typer(help="Manage memory versions.")


@version_app.command("create")
@command_errors
def create(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    content: str = typer.Option(..., help="New version content."),
    context: str | None = typer.Option(None, help="Where the knowledge applies."),
    git_branch: str | None = typer.Option(None, help="Git branch name."),
    git_commit: str | None = typer.Option(None, help="Git commit hash."),
    git_description: str | None = typer.Option(None, help="Git change description."),
    branch: str | None = typer.Option(
        None, "--branch", help="Chronicle branch id. Defaults to the parent the version's memory."
    ),
) -> None:
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    git_ctx = None
    if any([git_branch, git_commit, git_description]):
        from chronicle.core.git import GitContext

        git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
    version = engine.create_version(
        memory_id=memory_uuid,
        content=content,
        context=context,
        git_context=git_ctx,
        branch_id=branch,
    )
    memory = engine.get_memory(memory_uuid)
    label = memory.name if memory and memory.name else memory_uuid
    typer.echo(f'Created version v{version.sequence} of "{label}"')
    typer.echo(f"  sequence: {version.sequence}")
    typer.echo(f"  id: {version.id}")


@version_app.command("show")
@command_errors
def show(
    memory: str | None = typer.Option(None, help="Memory name."),
    memory_id: str | None = typer.Option(None, help="Memory UUID."),
    project: str | None = typer.Option(None, help="Project name (scopes name lookup)."),
    project_id: str | None = typer.Option(None, help="Project UUID."),
    sequence: int = typer.Option(..., help="Version sequence number."),
) -> None:
    engine = ctx.engine()
    memory_uuid = get_memory_id(
        engine, memory=memory, memory_id=memory_id, project=project, project_id=project_id
    )
    version = engine.get_version(memory_id=memory_uuid, sequence=sequence)
    if version is None:
        typer.secho(f"Version not found: {memory_uuid} v{sequence}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)
    memory = engine.get_memory(memory_uuid)
    label = memory.name if memory and memory.name else memory_uuid
    typer.echo(f'Version v{version.sequence} of "{label}"')
    typer.echo(f"  sequence: {version.sequence}")
    typer.echo(f"  content: {version.content}")
    if version.context:
        typer.echo(f"  context: {version.context}")
    git_ctx = version.git_context
    if git_ctx:
        typer.echo("  git_context:")
        for key, value in git_ctx.items():
            typer.echo(f"    {key}: {value}")
    evidence = version.evidence
    if evidence:
        typer.echo("  evidence:")
        for e in evidence:
            typer.echo(f"    [{e.evidence_type}] {e.ref}")
