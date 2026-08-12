"""Fetch configured job sources and persist normalized postings."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from core.interfaces import JobSource
from core.logging import configure_json_logging
from db.jobs import upsert_job
from db.session import create_engine_and_session
from sources.registry import create_source

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScrapeResult:
    fetched: int
    created: int
    updated: int


def run(
    sources: Iterable[JobSource], session: Session, since: datetime | None = None
) -> ScrapeResult:
    """Fetch sources and commit normalized postings in one transaction."""
    fetched = created = 0
    for source in sources:
        for posting in source.fetch(since=since):
            fetched += 1
            _, was_created = upsert_job(session, posting)
            created += was_created
    session.commit()
    return ScrapeResult(fetched=fetched, created=created, updated=fetched - created)


def main() -> None:
    configure_json_logging()
    parser = argparse.ArgumentParser(
        description="Fetch and persist internship listings."
    )
    parser.add_argument(
        "--source", action="append", choices=("internshala", "remotive")
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("provide --database-url or set DATABASE_URL")

    engine, session_factory = create_engine_and_session(arguments.database_url)
    try:
        with session_factory() as session:
            result = run(
                [
                    create_source(name)
                    for name in arguments.source or ("internshala", "remotive")
                ],
                session,
            )
        logger.info(
            "scrape completed",
            extra={
                "fetched": result.fetched,
                "created": result.created,
                "updated": result.updated,
            },
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
