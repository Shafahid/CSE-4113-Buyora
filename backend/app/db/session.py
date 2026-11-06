from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 10,
            # Supabase transaction poolers do not support prepared statements.
            "prepare_threshold": None,
        },
    )


def get_db(request: Request) -> Iterator[Session]:
    """Close every request's session; write operations must explicitly commit."""
    with request.app.state.session_factory() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]
