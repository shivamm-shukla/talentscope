import json

from core.models import JobPosting, MatchedJob, User
from notifications.email_notifier import EmailNotifier
from notifications.telegram_notifier import TelegramNotifier


def user(**overrides) -> User:
    values = {"id": 1, "email": "student@example.test"}
    values.update(overrides)
    return User(**values)


def matched_job() -> MatchedJob:
    return MatchedJob(
        job=JobPosting(
            source="fixture",
            title="Python Intern",
            company="Example Co",
            location="Remote",
            link="https://example.test/jobs/1",
        ),
        score=0.7,
        reasons=("skills: python",),
    )


class FakeSmtpConnection:
    def __init__(self) -> None:
        self.sent_messages = []

    def __enter__(self) -> "FakeSmtpConnection":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def send_message(self, message: object) -> None:
        self.sent_messages.append(message)


def test_email_notifier_sends_digest() -> None:
    connection = FakeSmtpConnection()
    notifier = EmailNotifier(
        sender_address="bot@talentscope.test", smtp_factory=lambda: connection
    )

    result = notifier.send(user(), [matched_job()])

    assert result.delivered is True
    assert result.channel == "email"
    assert len(connection.sent_messages) == 1
    assert connection.sent_messages[0]["To"] == "student@example.test"


def test_email_notifier_skips_when_no_matches() -> None:
    notifier = EmailNotifier(sender_address="bot@talentscope.test", smtp_factory=None)

    result = notifier.send(user(), [])

    assert result.delivered is False


def test_email_notifier_skips_when_user_has_no_email() -> None:
    notifier = EmailNotifier(sender_address="bot@talentscope.test", smtp_factory=None)

    result = notifier.send(user(email=""), [matched_job()])

    assert result.delivered is False
    assert "email" in result.detail


def test_email_notifier_reports_smtp_failure() -> None:
    def failing_factory():
        raise OSError("connection refused")

    notifier = EmailNotifier(
        sender_address="bot@talentscope.test", smtp_factory=failing_factory
    )

    result = notifier.send(user(), [matched_job()])

    assert result.delivered is False
    assert "connection refused" in result.detail


def test_telegram_notifier_sends_digest() -> None:
    captured = {}

    def poster(url: str, payload: bytes) -> bytes:
        captured["url"] = url
        captured["payload"] = json.loads(payload)
        return json.dumps({"ok": True}).encode("utf-8")

    notifier = TelegramNotifier(bot_token="TOKEN", poster=poster)

    result = notifier.send(user(telegram_chat_id="123"), [matched_job()])

    assert result.delivered is True
    assert captured["url"].endswith("/botTOKEN/sendMessage")
    assert captured["payload"]["chat_id"] == "123"


def test_telegram_notifier_skips_without_chat_id() -> None:
    notifier = TelegramNotifier(bot_token="TOKEN", poster=lambda *_: b"")

    result = notifier.send(user(), [matched_job()])

    assert result.delivered is False
    assert "chat id" in result.detail


def test_telegram_notifier_reports_api_error() -> None:
    def poster(_url: str, _payload: bytes) -> bytes:
        return json.dumps({"ok": False, "description": "bot blocked"}).encode("utf-8")

    notifier = TelegramNotifier(bot_token="TOKEN", poster=poster)

    result = notifier.send(user(telegram_chat_id="123"), [matched_job()])

    assert result.delivered is False
    assert result.detail == "bot blocked"


def test_telegram_notifier_reports_transport_failure() -> None:
    def poster(_url: str, _payload: bytes) -> bytes:
        raise OSError("timed out")

    notifier = TelegramNotifier(bot_token="TOKEN", poster=poster)

    result = notifier.send(user(telegram_chat_id="123"), [matched_job()])

    assert result.delivered is False
    assert "timed out" in result.detail
