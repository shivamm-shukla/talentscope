"""Match persisted jobs to user preferences and record the results."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.models import JobPosting, UserPreferences
from db.matches import upsert_match
from db.models import Job, User
from db.session import create_engine_and_session
from matching.matcher import match_jobs


@dataclass(frozen=True, slots=True)
class MatchResult:
    users_processed: int
    created: int
    updated: int


def _job_posting(job: Job) -> JobPosting:
    return JobPosting(
        source=job.source,
        title=job.title,
        company=job.company,
        location=job.location,
        link=job.link,
        posted_at=job.posted_at,
        scraped_at=job.scraped_at,
        salary_raw=job.salary_raw,
        salary_numeric=job.salary_numeric,
        skills=tuple(job.skills),
    )


def _preferences(user: User) -> UserPreferences:
    if user.preferences is None:
        return UserPreferences()
    return UserPreferences(
        skills=tuple(user.preferences.skills),
        locations=tuple(user.preferences.locations),
        minimum_stipend=user.preferences.minimum_stipend,
        channels=tuple(user.preferences.preferred_channels),
    )


def run(session: Session) -> MatchResult:
    """Compute and persist matches for every user with stored preferences."""
    jobs = list(session.scalars(select(Job)).all())
    users = list(
        session.scalars(select(User).options(selectinload(User.preferences))).all()
    )
    jobs_by_identity = {
        (job.source, job.title, job.company, job.location): job for job in jobs
    }
    created = updated = 0
    for user in users:
        for matched in match_jobs(
            _preferences(user), [_job_posting(job) for job in jobs]
        ):
            key = (
                matched.job.source,
                matched.job.title,
                matched.job.company,
                matched.job.location,
            )
            _, was_created = upsert_match(session, user, jobs_by_identity[key], matched)
            created += was_created
            updated += not was_created
    session.commit()
    return MatchResult(users_processed=len(users), created=created, updated=updated)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match stored jobs to user preferences."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("provide --database-url or set DATABASE_URL")
    engine, session_factory = create_engine_and_session(arguments.database_url)
    try:
        with session_factory() as session:
            result = run(session)
        print(
            f"Processed {result.users_processed}; created {result.created}; "
            f"updated {result.updated}."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
