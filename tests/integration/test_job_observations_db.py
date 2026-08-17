from datetime import datetime, timedelta, timezone

from db.job_observations import (
    observed_at_for_job,
    prune_observations_older_than,
    record_observation,
)
from db.models import Base, Job
from db.session import create_engine_and_session

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)


def make_job() -> Job:
    return Job(
        source="fixture",
        title="Python Intern",
        company="Example Co",
        location="Remote",
        link="https://example.test/jobs/1",
        skills=["python"],
    )


def test_record_and_read_observations_in_order() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        job = make_job()
        session.add(job)
        session.commit()

        record_observation(session, job, observed_at=NOW - timedelta(hours=2))
        record_observation(session, job, observed_at=NOW)
        session.commit()

        timestamps = observed_at_for_job(session, job.id)

    engine.dispose()
    naive = [t.replace(tzinfo=None) for t in timestamps]
    assert naive == [
        (NOW - timedelta(hours=2)).replace(tzinfo=None),
        NOW.replace(tzinfo=None),
    ]


def test_prune_observations_older_than_cutoff() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        job = make_job()
        session.add(job)
        session.commit()

        record_observation(session, job, observed_at=NOW - timedelta(days=40))
        record_observation(session, job, observed_at=NOW)
        session.commit()

        deleted = prune_observations_older_than(
            session, cutoff=NOW - timedelta(days=30)
        )
        session.commit()
        timestamps = observed_at_for_job(session, job.id)

    engine.dispose()
    assert deleted == 1
    assert [t.replace(tzinfo=None) for t in timestamps] == [NOW.replace(tzinfo=None)]
