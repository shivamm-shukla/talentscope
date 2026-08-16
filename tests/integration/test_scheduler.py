import logging

from core.models import DeliveryResult, JobPosting
from db.models import Base, Job, User, UserPreference
from db.session import create_engine_and_session
from workers.scheduler import run_pipeline


class FakeSource:
    name = "fixture"

    def fetch(self, since=None):
        return [
            JobPosting(
                source="fixture",
                title="Python Intern",
                company="Example Co",
                location="Remote",
                link="https://example.test/jobs/1",
                skills=("python",),
                salary_raw="15k per month",
            )
        ]


class FailingSource:
    name = "broken"

    def fetch(self, since=None):
        raise RuntimeError("source unreachable")


class FakeNotifier:
    channel = "email"

    def send(self, user, matches):
        return DeliveryResult(channel=self.channel, delivered=True, detail="ok")


def _seeded_session_factory():
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        user.preferences = UserPreference(
            skills=["python"], preferred_channels=["email"]
        )
        session.add(user)
        session.commit()
    return engine, session_factory


def test_run_pipeline_runs_all_stages_end_to_end() -> None:
    engine, session_factory = _seeded_session_factory()

    run_pipeline(
        session_factory, [FakeSource()], notifier_factory=lambda _: FakeNotifier()
    )

    with session_factory() as session:
        job = session.query(Job).one()
        assert job.salary_numeric == 15_000
        assert session.query(User).one().matches

    engine.dispose()


def test_run_pipeline_isolates_a_failing_source_from_others(caplog) -> None:
    engine, session_factory = _seeded_session_factory()

    with caplog.at_level(logging.ERROR):
        run_pipeline(
            session_factory,
            [FakeSource(), FailingSource()],
            notifier_factory=lambda _: FakeNotifier(),
        )

    assert "source broken failed to fetch" in caplog.text
    with session_factory() as session:
        assert session.query(Job).count() == 1

    engine.dispose()
