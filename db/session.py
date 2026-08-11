"""SQLAlchemy engine and session creation, with no application-global state."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine_and_session(
    database_url: str,
) -> tuple[Engine, sessionmaker[Session]]:
    """Create an engine and a reusable session factory for *database_url*.

    Callers own the engine lifecycle. Keeping it explicit makes workers and tests
    independent and prevents importing this module from opening a database connection.
    """
    engine = create_engine(database_url)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
