"""Persistence operations for tracked job applications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db.models import APPLICATION_STATUSES, Application, Job, User

REMINDER_WINDOW_DAYS = 3
REMINDER_ELIGIBLE_STATUSES = ("saved", "applied")


def get_or_create(
    session: Session, user: User, job: Job, status: str = "saved"
) -> Application:
    """Return the user's existing application for *job*, creating one if absent.

    A freshly created application always starts at "saved" and, if a
    different *status* was requested, immediately transitions through
    `set_status` — so status-specific side effects (history entry,
    `applied_at` stamping) happen the same way whether a status was set at
    creation time or via a later PATCH.
    """
    statement = select(Application).where(
        Application.user_id == user.id, Application.job_id == job.id
    )
    application = session.scalar(statement)
    if application is None:
        now = datetime.now(UTC)
        application = Application(
            user=user,
            job=job,
            status="saved",
            status_history=[{"status": "saved", "at": now.isoformat()}],
        )
        session.add(application)
        if status != "saved":
            set_status(session, application, status)
    return application


def set_status(session: Session, application: Application, status: str) -> Application:
    """Transition *application* to *status*, appending to its history."""
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"unknown application status: {status!r}")
    now = datetime.now(UTC)
    application.status = status
    application.status_history = [
        *application.status_history,
        {"status": status, "at": now.isoformat()},
    ]
    if status == "applied" and application.applied_at is None:
        application.applied_at = now
    return application


def list_for_user(session: Session, user: User) -> list[Application]:
    return list(
        session.scalars(
            select(Application)
            .where(Application.user_id == user.id)
            .order_by(Application.updated_at.desc())
        ).all()
    )


def statuses_by_job_id(session: Session, user: User) -> dict[int, str]:
    """Map ``job_id -> status`` for every application *user* has, for cheap
    lookup when annotating a list of jobs (e.g. the matches feed)."""
    rows = session.scalars(
        select(Application).where(Application.user_id == user.id)
    ).all()
    return {application.job_id: application.status for application in rows}


def due_for_deadline_reminder(
    session: Session,
    now: datetime | None = None,
    window_days: int = REMINDER_WINDOW_DAYS,
) -> list[Application]:
    """Applications still worth a deadline nudge: not yet past "applied"
    (interviewing/offer/rejected/withdrawn have moved on from "should I
    apply?"), whose job has a real, source-confirmed deadline (never true
    for Remotive postings, which don't carry one) falling within
    *window_days* and not already passed.
    """
    now = now or datetime.now(UTC)
    cutoff = now + timedelta(days=window_days)
    statement = (
        select(Application)
        .join(Application.job)
        .where(
            Application.status.in_(REMINDER_ELIGIBLE_STATUSES),
            Job.deadline_at.is_not(None),
            Job.deadline_at >= now,
            Job.deadline_at <= cutoff,
        )
        .options(selectinload(Application.job), selectinload(Application.user))
    )
    return list(session.scalars(statement).all())
