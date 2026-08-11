from datetime import datetime

from core.models import JobPosting
from db.models import Base, Job
from db.session import create_engine_and_session
from workers.run_scrape import run


class FakeSource:
    name = "fixture"

    def __init__(self, jobs: list[JobPosting]) -> None:
        self.jobs = jobs

    def fetch(self, since=None) -> list[JobPosting]:
        return self.jobs


def make_posting(link: str = "https://example.test/jobs/1") -> JobPosting:
    return JobPosting(
        source="fixture",
        title="Python Intern",
        company="Example Co",
        location="Remote",
        link=link,
        skills=("python",),
        scraped_at=datetime(2026, 8, 11),
    )


def test_scrape_worker_creates_then_updates_jobs() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        first = run([FakeSource([make_posting()])], session)
        second = run(
            [FakeSource([make_posting("https://example.test/jobs/updated")])], session
        )
        stored = session.query(Job).one()

    engine.dispose()

    assert first.fetched == 1 and first.created == 1 and first.updated == 0
    assert second.fetched == 1 and second.created == 0 and second.updated == 1
    assert stored.link == "https://example.test/jobs/updated"
