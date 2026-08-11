"""Persistence operations for user-job matches."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import MatchedJob
from db.models import Job, Match, User


def upsert_match(
    session: Session, user: User, job: Job, match: MatchedJob
) -> tuple[Match, bool]:
    """Insert or refresh a match, storing its score as an integer percentage."""
    statement = select(Match).where(Match.user_id == user.id, Match.job_id == job.id)
    stored = session.scalar(statement)
    created = stored is None
    if stored is None:
        stored = Match(user=user, job=job, score=0, reasons=[])
        session.add(stored)
    stored.score = round(match.score * 100)
    stored.reasons = list(match.reasons)
    return stored, created
