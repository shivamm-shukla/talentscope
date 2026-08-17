from datetime import datetime, timedelta, timezone

from core.models import JobPosting
from db.job_observations import observed_at_for_job
from db.models import Base, Job
from db.session import create_engine_and_session
from workers.run_scrape import run

FIXED_NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)


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
        first = run([FakeSource([make_posting()])], session, now=FIXED_NOW)
        second = run(
            [FakeSource([make_posting("https://example.test/jobs/updated")])],
            session,
            now=FIXED_NOW,
        )
        stored = session.query(Job).one()

    engine.dispose()

    assert first.fetched == 1 and first.created == 1 and first.updated == 0
    assert second.fetched == 1 and second.created == 0 and second.updated == 1
    assert stored.link == "https://example.test/jobs/updated"
    assert stored.listing_type == "internship"
    assert stored.work_mode == "remote"
    assert stored.expires_at is not None


def test_scrape_worker_skips_postings_outside_cs_scope() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    non_cs = JobPosting(
        source="fixture",
        title="Retail Store Associate",
        company="Example Mart",
        location="Mumbai",
        link="https://example.test/jobs/retail",
        scraped_at=datetime(2026, 8, 11),
    )

    with session_factory() as session:
        result = run([FakeSource([non_cs])], session, now=FIXED_NOW)
        stored = session.query(Job).all()

    engine.dispose()

    assert result.fetched == 1
    assert result.created == 0
    assert result.skipped_non_cs == 1
    assert stored == []


def test_scrape_worker_skips_already_expired_postings() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    stale = JobPosting(
        source="fixture",
        title="Python Intern",
        company="Example Co",
        location="Remote",
        link="https://example.test/jobs/stale",
        skills=("python",),
        posted_at=FIXED_NOW - timedelta(days=90),
    )

    with session_factory() as session:
        result = run([FakeSource([stale])], session, now=FIXED_NOW)
        stored = session.query(Job).all()

    engine.dispose()

    assert result.fetched == 1
    assert result.created == 0
    assert result.skipped_expired == 1
    assert stored == []


def test_scrape_worker_prunes_previously_stored_jobs_that_have_since_expired() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    posting = JobPosting(
        source="fixture",
        title="Python Intern",
        company="Example Co",
        location="Remote",
        link="https://example.test/jobs/1",
        skills=("python",),
        posted_at=FIXED_NOW,
    )

    with session_factory() as session:
        run([FakeSource([posting])], session, now=FIXED_NOW)
        later = FIXED_NOW + timedelta(days=60)
        result = run([FakeSource([])], session, now=later)
        stored = session.query(Job).all()

    engine.dispose()

    assert result.pruned == 1
    assert stored == []


def test_scrape_worker_persists_a_real_deadline_when_the_source_provides_one() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    deadline = FIXED_NOW + timedelta(days=20)
    posting = JobPosting(
        source="fixture",
        title="Python Intern",
        company="Example Co",
        location="Remote",
        link="https://example.test/jobs/1",
        skills=("python",),
        posted_at=FIXED_NOW,
        deadline_at=deadline,
    )
    with session_factory() as session:
        run([FakeSource([posting])], session, now=FIXED_NOW)
        stored = session.query(Job).one()

    engine.dispose()
    assert stored.deadline_at.replace(tzinfo=None) == deadline.replace(tzinfo=None)


def test_scrape_worker_records_one_observation_per_cycle_seen_in() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        run([FakeSource([make_posting()])], session, now=FIXED_NOW)
        later = FIXED_NOW + timedelta(hours=2)
        run([FakeSource([make_posting()])], session, now=later)
        job = session.query(Job).one()
        timestamps = observed_at_for_job(session, job.id)

    engine.dispose()
    naive = [t.replace(tzinfo=None) for t in timestamps]
    assert naive == [FIXED_NOW.replace(tzinfo=None), later.replace(tzinfo=None)]
