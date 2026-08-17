"""Persistence operations for the per-scrape-cycle job observation log."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db.models import Job, JobObservation


def record_observation(
    session: Session, job: Job, observed_at: datetime | None = None
) -> JobObservation:
    """Append one observation row for *job*, one per scrape cycle it's seen in."""
    observation = JobObservation(job=job)
    if observed_at is not None:
        observation.observed_at = observed_at
    session.add(observation)
    return observation


def observed_at_for_job(session: Session, job_id: int) -> list[datetime]:
    """Return *job_id*'s observation timestamps, oldest first."""
    return list(
        session.scalars(
            select(JobObservation.observed_at)
            .where(JobObservation.job_id == job_id)
            .order_by(JobObservation.observed_at.asc())
        ).all()
    )


def prune_observations_older_than(
    session: Session, cutoff: datetime | None = None
) -> int:
    """Delete observation rows older than *cutoff*, since they accumulate every
    scrape cycle and only recent gaps/cadence matter for scoring."""
    cutoff = cutoff or datetime.now(timezone.utc)
    result = session.execute(
        delete(JobObservation).where(JobObservation.observed_at < cutoff)
    )
    return result.rowcount or 0
