"""Fetch configured job sources and persist normalized postings."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from analysis.classify import classify
from core.interfaces import JobSource
from core.logging import configure_json_logging
from db.job_observations import prune_observations_older_than, record_observation
from db.jobs import prune_expired_jobs, upsert_job
from db.session import create_engine_and_session
from sources.registry import create_source

logger = logging.getLogger(__name__)

OBSERVATION_RETENTION_DAYS = 30


@dataclass(frozen=True, slots=True)
class ScrapeResult:
    fetched: int
    created: int
    updated: int
    skipped_non_cs: int = 0
    skipped_expired: int = 0
    pruned: int = 0


def run(
    sources: Iterable[JobSource],
    session: Session,
    since: datetime | None = None,
    now: datetime | None = None,
) -> ScrapeResult:
    """Fetch sources and commit normalized postings in one transaction.

    Postings outside the product's scope are dropped rather than stored:
    non-CS/BCA-relevant postings (`skipped_non_cs`), and postings whose
    estimated application window has already lapsed (`skipped_expired`).
    Previously-stored postings that have since expired are also pruned.
    """
    now = now or datetime.now(timezone.utc)
    fetched = created = skipped_non_cs = skipped_expired = 0
    for source in sources:
        try:
            postings = source.fetch(since=since)
        except Exception:
            logger.exception("source %s failed to fetch; skipping", source.name)
            continue
        for posting in postings:
            fetched += 1
            classification = classify(posting, now=now)
            if not classification.is_cs_related:
                skipped_non_cs += 1
                continue
            if classification.expires_at < now:
                skipped_expired += 1
                continue
            job, was_created = upsert_job(session, posting, classification)
            created += was_created
            record_observation(session, job, observed_at=now)
    processed = fetched - skipped_non_cs - skipped_expired
    pruned = prune_expired_jobs(session, now=now)
    prune_observations_older_than(
        session, cutoff=now - timedelta(days=OBSERVATION_RETENTION_DAYS)
    )
    session.commit()
    return ScrapeResult(
        fetched=fetched,
        created=created,
        updated=processed - created,
        skipped_non_cs=skipped_non_cs,
        skipped_expired=skipped_expired,
        pruned=pruned,
    )


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
                "skipped_non_cs": result.skipped_non_cs,
                "skipped_expired": result.skipped_expired,
                "pruned": result.pruned,
            },
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
