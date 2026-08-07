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
) -> None:
    version = ctx.engine().create_version(memory_id=memory_id, content=content, context=context)
    typer.echo(f"Created version {version.id}")
    typer.echo(f"  memory: {version.memory_id}")
    typer.echo(f"  sequence: {version.sequence}")
