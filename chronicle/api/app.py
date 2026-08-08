from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from chronicle import __version__
from chronicle.api.routes import router
from chronicle.core import (
    ChronicleEngine,
    ChronicleError,
    CrossProjectRelationshipError,
    GitContextError,
    InvalidObservationActionError,
    MemoryNotFoundError,
    ObservationAlreadyProcessedError,
    ObservationNotFoundError,
    ProjectNotFoundError,
    RelationshipNotFoundError,
    SearchQueryError,
    SelfRelationshipError,
)

DEFAULT_DB_PATH = Path(".chronicle") / "chronicle.db"

_STATUS_CODES: dict[type[ChronicleError], int] = {
    ProjectNotFoundError: 404,
    MemoryNotFoundError: 404,
    ObservationNotFoundError: 404,
    RelationshipNotFoundError: 404,
    SearchQueryError: 400,
    GitContextError: 400,
    InvalidObservationActionError: 400,
    ObservationAlreadyProcessedError: 400,
    SelfRelationshipError: 400,
    CrossProjectRelationshipError: 400,
}


def default_session_factory() -> sessionmaker[Session]:
    database = create_engine(f"sqlite:///{DEFAULT_DB_PATH}")
    return sessionmaker(bind=database)


def _chronicle_error_handler(request: Request, exc: ChronicleError) -> JSONResponse:
    status_code = _STATUS_CODES.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def create_app(session_factory: sessionmaker[Session] | None = None) -> FastAPI:
    """Build a Chronicle REST application.

    The engine is constructed once from a session factory and attached to the
    application state. Route handlers never touch SQLAlchemy directly; they
    delegate exclusively to ``ChronicleEngine``.
    """
    app = FastAPI(title="Chronicle REST API", version=__version__)
    app.state.engine = ChronicleEngine(session_factory or default_session_factory())
    app.add_exception_handler(ChronicleError, _chronicle_error_handler)
    app.include_router(router)
    return app


app = create_app()
