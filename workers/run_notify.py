"""Send unnotified matches to users over their preferred channels."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.interfaces import Notifier
from core.models import JobPosting, MatchedJob, UserPreferences
from core.models import User as DomainUser
from db.models import Match, User
from db.notifications import record_notification, unsent_matches
from db.session import create_engine_and_session
from notifications.registry import create_notifier


@dataclass(frozen=True, slots=True)
class NotifyResult:
    sent: int
    failed: int


def _domain_user(user: User) -> DomainUser:
    return DomainUser(
        id=user.id,
        email=user.email,
        name=user.name,
        preferences=UserPreferences(
            channels=(
                tuple(user.preferences.preferred_channels) if user.preferences else ()
            )
        ),
        telegram_chat_id=user.telegram_chat_id,
    )


def _matched_job(match: Match) -> MatchedJob:
    job = match.job
    return MatchedJob(
        job=JobPosting(
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
        ),
        score=match.score / 100,
        reasons=tuple(match.reasons),
    )


def run(session: Session, notifier_factory: Callable[[str], Notifier]) -> NotifyResult:
    """Send every user's unnotified matches over their preferred channels."""
    users = list(
        session.scalars(select(User).options(selectinload(User.preferences))).all()
    )
    notifiers: dict[str, Notifier] = {}
    sent = failed = 0
    for user in users:
        channels = user.preferences.preferred_channels if user.preferences else []
        for channel in channels:
            if channel not in notifiers:
                notifiers[channel] = notifier_factory(channel)
            matches = unsent_matches(session, user.id, channel)
            if not matches:
                continue
            result = notifiers[channel].send(
                _domain_user(user), [_matched_job(match) for match in matches]
            )
            for match in matches:
                record_notification(session, match, result)
            if result.delivered:
                sent += len(matches)
            else:
                failed += len(matches)
    session.commit()
    return NotifyResult(sent=sent, failed=failed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Notify users of their unsent job matches."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("provide --database-url or set DATABASE_URL")
    engine, session_factory = create_engine_and_session(arguments.database_url)
    try:
        with session_factory() as session:
            result = run(session, create_notifier)
        print(f"Sent {result.sent}; failed {result.failed}.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
