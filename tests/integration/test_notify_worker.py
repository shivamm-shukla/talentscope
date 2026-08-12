from core.models import DeliveryResult
from db.models import Base, Job, Match, NotificationSent, User, UserPreference
from db.session import create_engine_and_session
from workers.run_notify import run


class FakeNotifier:
    def __init__(self, channel: str, delivered: bool = True) -> None:
        self.channel = channel
        self.delivered = delivered
        self.calls = []

    def send(self, user, matches):
        self.calls.append((user, matches))
        return DeliveryResult(
            channel=self.channel, delivered=self.delivered, detail="ok"
        )


def _seed(session_factory):
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        user.preferences = UserPreference(preferred_channels=["email"])
        job = Job(
            source="fixture",
            title="Python Intern",
            company="Example Co",
            location="Remote",
            link="https://example.test/jobs/1",
            skills=["python"],
        )
        session.add_all([user, job])
        session.commit()
        match = Match(user=user, job=job, score=80, reasons=["skills: python"])
        session.add(match)
        session.commit()


def test_notify_worker_sends_and_records_unsent_matches() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    _seed(session_factory)
    notifier = FakeNotifier("email")

    with session_factory() as session:
        first = run(session, lambda channel: notifier)
        second = run(session, lambda channel: notifier)
        records = session.query(NotificationSent).all()

    engine.dispose()

    assert first.sent == 1 and first.failed == 0
    assert second.sent == 0 and second.failed == 0
    assert len(notifier.calls) == 1
    assert len(records) == 1
    assert records[0].status == "sent"


def test_notify_worker_records_failed_delivery() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    _seed(session_factory)
    notifier = FakeNotifier("email", delivered=False)

    with session_factory() as session:
        result = run(session, lambda channel: notifier)
        records = session.query(NotificationSent).all()

    engine.dispose()

    assert result.sent == 0 and result.failed == 1
    assert records[0].status == "failed"
