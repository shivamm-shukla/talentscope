"""Persistence operations for deadline reminder delivery records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import DeliveryResult
from db.models import Application, ReminderSent


def record_reminder(
    session: Session, application: Application, result: DeliveryResult
) -> tuple[ReminderSent, bool]:
    """Insert or refresh the reminder delivery record for *application* on
    *result.channel*."""
    statement = select(ReminderSent).where(
        ReminderSent.application_id == application.id,
        ReminderSent.channel == result.channel,
    )
    stored = session.scalar(statement)
    created = stored is None
    if stored is None:
        stored = ReminderSent(
            application=application, channel=result.channel, status="", detail=""
        )
        session.add(stored)
    stored.status = "sent" if result.delivered else "failed"
    stored.detail = result.detail
    return stored, created


def unreminded_applications(
    session: Session, applications: list[Application], channel: str
) -> list[Application]:
    """Return the subset of *applications* with no successful reminder
    delivery record on *channel*."""
    already_sent = select(ReminderSent.application_id).where(
        ReminderSent.channel == channel, ReminderSent.status == "sent"
    )
    sent_ids = {row for row in session.scalars(already_sent).all()}
    return [a for a in applications if a.id not in sent_ids]
