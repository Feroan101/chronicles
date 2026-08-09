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


def _migrations_dir() -> Path:
    """Resolve Chronicle's own Alembic migration scripts.

    Migrations are internal to Chronicle: they live either bundled inside the
    installed ``chronicle`` package (``chronicle/alembic``) or, in a source
    checkout, next to the package (``<chronicle parent>/alembic``). The target
    project's directory is never consulted, so ``chronicle init`` works in any
    project regardless of whether it uses Alembic.
    """
    package_dir = Path(__file__).resolve().parent.parent
    for candidate in (package_dir / "alembic", package_dir.parent / "alembic"):
        if candidate.is_dir():
            return candidate
    raise ctx.CliError(
        "Chronicle migrations not found in the installed package. Reinstall Chronicle."
    )


def _run_migrations() -> None:
    """Apply Chronicle's own migrations to the project-local database."""
    config = Config()
    config.set_main_option("script_location", str(_migrations_dir()))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{ctx.db_path()}")
    command.upgrade(config, "head")


def _write_config() -> None:
    config = {"db": ctx.DB_FILENAME, "schema_version": __version__}
    ctx.config_path().write_text(json.dumps(config, indent=2) + "\n")
