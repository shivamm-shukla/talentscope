"""SMTP-backed email notifier."""

from __future__ import annotations

import smtplib
from collections.abc import Callable
from email.message import EmailMessage

from core.models import DeadlineReminder, DeliveryResult, MatchedJob, User

SmtpFactory = Callable[[], smtplib.SMTP]


def smtp_factory(host: str, port: int, username: str, password: str) -> SmtpFactory:
    """Build a factory that opens an authenticated, TLS SMTP connection on demand."""

    def factory() -> smtplib.SMTP:
        connection = smtplib.SMTP(host, port, timeout=15)
        connection.starttls()
        connection.login(username, password)
        return connection

    return factory


def _format_body(matches: list[MatchedJob]) -> str:
    lines = [
        f"- {match.job.title} at {match.job.company} ({match.job.location}): "
        f"{match.job.link}"
        for match in matches
    ]
    return "New job matches:\n\n" + "\n".join(lines)


def _format_reminder_body(reminders: list[DeadlineReminder]) -> str:
    ordered = sorted(reminders, key=lambda reminder: reminder.deadline_at)
    lines = [
        f"- {reminder.job.title} at {reminder.job.company}: "
        f"apply by {reminder.deadline_at:%d %b} — {reminder.job.link}"
        for reminder in ordered
    ]
    return "Deadlines coming up:\n\n" + "\n".join(lines)


class EmailNotifier:
    """Sends match digests over SMTP (Gmail free tier at cohort scale)."""

    channel = "email"

    def __init__(
        self,
        sender_address: str,
        smtp_factory: SmtpFactory,
        subject: str = "New santa scout matches",
        reminder_subject: str = "Deadlines coming up on santa scout",
    ) -> None:
        self._sender_address = sender_address
        self._smtp_factory = smtp_factory
        self._subject = subject
        self._reminder_subject = reminder_subject

    def send(self, user: User, matches: list[MatchedJob]) -> DeliveryResult:
        if not matches:
            return DeliveryResult(
                channel=self.channel, delivered=False, detail="no matches to send"
            )
        if not user.email:
            return DeliveryResult(
                channel=self.channel,
                delivered=False,
                detail="user has no email address",
            )
        return self._send(user.email, self._subject, _format_body(matches))

    def remind(self, user: User, reminders: list[DeadlineReminder]) -> DeliveryResult:
        if not reminders:
            return DeliveryResult(
                channel=self.channel, delivered=False, detail="no reminders to send"
            )
        if not user.email:
            return DeliveryResult(
                channel=self.channel,
                delivered=False,
                detail="user has no email address",
            )
        return self._send(
            user.email, self._reminder_subject, _format_reminder_body(reminders)
        )

    def _send(self, to_address: str, subject: str, body: str) -> DeliveryResult:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender_address
        message["To"] = to_address
        message.set_content(body)

        try:
            with self._smtp_factory() as connection:
                connection.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            return DeliveryResult(
                channel=self.channel, delivered=False, detail=str(error)
            )
        return DeliveryResult(
            channel=self.channel, delivered=True, detail=f"sent to {to_address}"
        )
