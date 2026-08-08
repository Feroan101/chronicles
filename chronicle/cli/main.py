import typer

from chronicle.cli.init import init_command
from chronicle.cli.memory import memory_app
from chronicle.cli.project import project_app
from chronicle.cli.search import search_command
from chronicle.cli.version import version_app

app = typer.Typer(help="Chronicle: the shared memory layer for AI software engineering.")

app.command("init")(init_command)
app.command("search")(search_command)
app.add_typer(project_app, name="project")
app.add_typer(memory_app, name="memory")
app.add_typer(version_app, name="version")


if __name__ == "__main__":
    app()
