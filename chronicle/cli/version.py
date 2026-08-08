import typer

from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors

version_app = typer.Typer(help="Manage memory versions.")


@version_app.command("create")
@command_errors
def create(
    memory_id: str = typer.Option(..., help="Memory to extend."),
    content: str = typer.Option(..., help="New version content."),
    context: str | None = typer.Option(None, help="Where the knowledge applies."),
    git_branch: str | None = typer.Option(None, help="Git branch name."),
    git_commit: str | None = typer.Option(None, help="Git commit hash."),
    git_description: str | None = typer.Option(None, help="Git change description."),
) -> None:
    git_ctx = None
    if any([git_branch, git_commit, git_description]):
        from chronicle.core.git import GitContext

        git_ctx = GitContext(branch=git_branch, commit=git_commit, description=git_description)
    version = ctx.engine().create_version(
        memory_id=memory_id, content=content, context=context, git_context=git_ctx
    )
    typer.echo(f"Created version {version.id}")
    typer.echo(f"  memory: {version.memory_id}")
    typer.echo(f"  sequence: {version.sequence}")


@version_app.command("show")
@command_errors
def show(
    memory_id: str = typer.Option(..., help="Memory id."),
    sequence: int = typer.Option(..., help="Version sequence number."),
) -> None:
    engine = ctx.engine()
    version = engine.get_version(memory_id=memory_id, sequence=sequence)
    if version is None:
        typer.secho(f"Version not found: {memory_id} v{sequence}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.echo(f"Version {version.id}")
    typer.echo(f"  memory: {version.memory_id}")
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
