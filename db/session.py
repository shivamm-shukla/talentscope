"""SQLAlchemy engine and session creation, with no application-global state."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_engine_and_session(
    database_url: str,
) -> tuple[Engine, sessionmaker[Session]]:
    """Create an engine and a reusable session factory for *database_url*."""
    engine = create_engine(database_url)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine, sessionmaker(bind=engine, expire_on_commit=False)
