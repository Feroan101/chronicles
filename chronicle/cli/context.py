from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chronicle.core import ChronicleEngine, ChronicleError

CHRONICLE_DIR_NAME = ".chronicle"
DB_FILENAME = "chronicle.db"
CONFIG_FILENAME = "config.json"


class CliError(Exception):
    """Base class for CLI-layer errors."""


class ChronicleNotInitializedError(CliError):
    """Raised when an operation needs an initialized Chronicle."""


def chronicle_dir() -> Path:
    return Path.cwd() / CHRONICLE_DIR_NAME


def db_path() -> Path:
    return chronicle_dir() / DB_FILENAME


def config_path() -> Path:
    return chronicle_dir() / CONFIG_FILENAME


def is_initialized() -> bool:
    return db_path().is_file()


def engine() -> ChronicleEngine:
    if not is_initialized():
        raise ChronicleNotInitializedError(
            f"Chronicle is not initialized in {Path.cwd()}. Run 'chronicle init' first."
        )
    database = create_engine(f"sqlite:///{db_path()}")
    return ChronicleEngine(sessionmaker(bind=database))


def command_errors[F: Callable[..., Any]](func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ChronicleError as exc:
            typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from None
        except CliError as exc:
            typer.secho(str(exc), err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from None

    return wrapper
