"""Send deadline reminders for tracked applications nearing their deadline."""

from __future__ import annotations

import argparse
import logging
import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from core.interfaces import Notifier
from core.logging import configure_json_logging
from core.models import DeadlineReminder, JobPosting, UserPreferences
from core.models import User as DomainUser
from db.applications import due_for_deadline_reminder
from db.models import Application
from db.reminders import record_reminder, unreminded_applications
from db.session import create_engine_and_session
from notifications.registry import create_notifier

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RemindResult:
    sent: int
    failed: int


def _domain_user(user) -> DomainUser:
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


def _deadline_reminder(application: Application) -> DeadlineReminder:
    job = application.job
    return DeadlineReminder(
        job=JobPosting(
            source=job.source,
            title=job.title,
            company=job.company,
            location=job.location,
            link=job.link,
        ),
        deadline_at=job.deadline_at,
        application_status=application.status,
    )


def run(session: Session, notifier_factory: Callable[[str], Notifier]) -> RemindResult:
    """Send one deadline reminder per due, unreminded application, grouped
    by user and preferred channel."""
    applications = due_for_deadline_reminder(session)
    by_user: dict[int, list[Application]] = defaultdict(list)
    for application in applications:
        by_user[application.user_id].append(application)

    notifiers: dict[str, Notifier] = {}
    sent = failed = 0
    for user_applications in by_user.values():
        user = user_applications[0].user
        channels = user.preferences.preferred_channels if user.preferences else []
        for channel in channels:
            pending = unreminded_applications(session, user_applications, channel)
            if not pending:
                continue
            if channel not in notifiers:
                notifiers[channel] = notifier_factory(channel)
            reminders = [_deadline_reminder(a) for a in pending]
            result = notifiers[channel].remind(_domain_user(user), reminders)
            for application in pending:
                record_reminder(session, application, result)
            if result.delivered:
                sent += len(pending)
            else:
                failed += len(pending)
    session.commit()
    return RemindResult(sent=sent, failed=failed)


def main() -> None:
    configure_json_logging()
    parser = argparse.ArgumentParser(
        description="Send deadline reminders for tracked applications."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("provide --database-url or set DATABASE_URL")
    engine, session_factory = create_engine_and_session(arguments.database_url)
    try:
        with session_factory() as session:
            result = run(session, create_notifier)
        logger.info(
            "remind completed", extra={"sent": result.sent, "failed": result.failed}
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
