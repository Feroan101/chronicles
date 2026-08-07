import json
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

from chronicle import __version__
from chronicle.cli import context as ctx
from chronicle.cli.context import command_errors


@command_errors
def init_command() -> None:
    directory = ctx.chronicle_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _run_migrations()
    _write_config()
    typer.secho(f"Initialized Chronicle in {directory}", fg=typer.colors.GREEN)


def _run_migrations() -> None:
    ini = Path.cwd() / "alembic.ini"
    if not ini.is_file():
        raise ctx.CliError(
            f"alembic.ini not found in {Path.cwd()}. Run 'chronicle init' from the project root."
        )
    config = Config(str(ini))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{ctx.db_path()}")
    command.upgrade(config, "head")


def _write_config() -> None:
    config = {"db": ctx.DB_FILENAME, "schema_version": __version__}
    ctx.config_path().write_text(json.dumps(config, indent=2) + "\n")
