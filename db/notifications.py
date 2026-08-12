"""Persistence operations for notification delivery records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import DeliveryResult
from db.models import Match, NotificationSent


def record_notification(
    session: Session, match: Match, result: DeliveryResult
) -> tuple[NotificationSent, bool]:
    """Insert or refresh the delivery record for *match* on *result.channel*."""
    statement = select(NotificationSent).where(
        NotificationSent.match_id == match.id,
        NotificationSent.channel == result.channel,
    )
    stored = session.scalar(statement)
    created = stored is None
    if stored is None:
        stored = NotificationSent(
            user=match.user, match=match, channel=result.channel, status="", detail=""
        )
        session.add(stored)
    stored.status = "sent" if result.delivered else "failed"
    stored.detail = result.detail
    return stored, created


def unsent_matches(session: Session, user_id: int, channel: str) -> list[Match]:
    """Return *user_id*'s matches with no successful delivery record on *channel*."""
    already_sent = select(NotificationSent.match_id).where(
        NotificationSent.channel == channel, NotificationSent.status == "sent"
    )
    statement = select(Match).where(
        Match.user_id == user_id, Match.id.not_in(already_sent)
    )
    return list(session.scalars(statement).all())
