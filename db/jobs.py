"""Persistence operations for normalized job postings."""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from analysis.classify import Classification
from core.models import JobPosting
from db.models import Job


def upsert_job(
    session: Session, posting: JobPosting, classification: Classification | None = None
) -> tuple[Job, bool]:
    """Insert a posting or refresh its mutable fields; return it and creation status."""
    statement = select(Job).where(
        Job.source == posting.source,
        Job.title == posting.title,
        Job.company == posting.company,
        Job.location == posting.location,
    )
    job = session.scalar(statement)
    created = job is None
    if job is None:
        job = Job(
            source=posting.source,
            title=posting.title,
            company=posting.company,
            location=posting.location,
            link=posting.link,
        )
        session.add(job)

    job.link = posting.link
    job.salary_raw = posting.salary_raw
    job.salary_numeric = posting.salary_numeric
    job.skills = list(posting.skills)
    job.posted_at = posting.posted_at
    if posting.scraped_at is not None:
        job.scraped_at = posting.scraped_at
    if classification is not None:
        job.listing_type = classification.listing_type
        job.work_mode = classification.work_mode
        job.pay_type = classification.pay_type
        job.duration_months = classification.duration_months
        job.target_year = classification.target_year
        job.expires_at = classification.expires_at
    return job, created


def prune_expired_jobs(session: Session, now: datetime | None = None) -> int:
    """Delete postings whose application window has passed, per retention policy."""
    now = now or datetime.now(timezone.utc)
    result = session.execute(
        delete(Job).where(Job.expires_at.is_not(None), Job.expires_at < now)
    )
    return result.rowcount or 0
