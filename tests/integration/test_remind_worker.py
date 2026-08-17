from datetime import UTC, datetime, timedelta

from core.models import DeliveryResult
from db.applications import get_or_create
from db.models import Base, Job, ReminderSent, User, UserPreference
from db.session import create_engine_and_session
from workers.run_remind import run


class FakeNotifier:
    def __init__(self, channel: str, delivered: bool = True) -> None:
        self.channel = channel
        self.delivered = delivered
        self.calls = []

    def remind(self, user, reminders):
        self.calls.append((user, reminders))
        return DeliveryResult(
            channel=self.channel, delivered=self.delivered, detail="ok"
        )


def _seed(session_factory, *, deadline_at, status="saved"):
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        user.preferences = UserPreference(preferred_channels=["email"])
        job = Job(
            source="internshala",
            title="Python Intern",
            company="Example Co",
            location="Remote",
            link="https://example.test/jobs/1",
            skills=["python"],
            deadline_at=deadline_at,
        )
        session.add_all([user, job])
        session.commit()
        application = get_or_create(session, user, job, status=status)
        session.commit()
        return application.id


def test_remind_worker_sends_once_and_dedups_on_second_run() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    _seed(session_factory, deadline_at=datetime.now(UTC) + timedelta(days=1))
    notifier = FakeNotifier("email")

    with session_factory() as session:
        first = run(session, lambda channel: notifier)
        second = run(session, lambda channel: notifier)
        records = session.query(ReminderSent).all()

    engine.dispose()
    assert first.sent == 1 and first.failed == 0
    assert second.sent == 0 and second.failed == 0
    assert len(notifier.calls) == 1
    assert len(records) == 1
    assert records[0].status == "sent"


def test_remind_worker_retries_after_a_failed_send() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    _seed(session_factory, deadline_at=datetime.now(UTC) + timedelta(days=1))
    notifier = FakeNotifier("email", delivered=False)

    with session_factory() as session:
        result = run(session, lambda channel: notifier)
        records = session.query(ReminderSent).all()

    engine.dispose()
    assert result.sent == 0 and result.failed == 1
    assert records[0].status == "failed"


def test_remind_worker_skips_applications_outside_the_reminder_window() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    _seed(session_factory, deadline_at=datetime.now(UTC) + timedelta(days=30))
    notifier = FakeNotifier("email")

    with session_factory() as session:
        result = run(session, lambda channel: notifier)

    engine.dispose()
    assert result.sent == 0 and result.failed == 0
    assert notifier.calls == []


def test_remind_worker_skips_applications_past_the_apply_decision() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    _seed(
        session_factory,
        deadline_at=datetime.now(UTC) + timedelta(days=1),
        status="rejected",
    )
    notifier = FakeNotifier("email")

    with session_factory() as session:
        result = run(session, lambda channel: notifier)

    engine.dispose()
    assert result.sent == 0
    assert notifier.calls == []
