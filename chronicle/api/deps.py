from typing import Annotated

from fastapi import Depends, Request

from chronicle.core import ChronicleEngine


def get_engine(request: Request) -> ChronicleEngine:
    """Resolve the engine bound to the running application.

    The engine is created once per application instance and holds only a
    session factory; every request opens and closes its own database session
    inside ``ChronicleEngine`` transactions.
    """
    return request.app.state.engine


Engine = Annotated[ChronicleEngine, Depends(get_engine)]
