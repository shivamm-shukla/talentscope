"""Persistence operations for normalized job postings."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import JobPosting
from db.models import Job


def upsert_job(session: Session, posting: JobPosting) -> tuple[Job, bool]:
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
    return job, created
