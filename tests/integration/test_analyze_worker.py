from db.models import Base, Job
from db.session import create_engine_and_session
from workers.run_analyze import run


def _job(**overrides) -> Job:
    values = {
        "source": "fixture",
        "title": "Python Intern",
        "company": "Example Co",
        "location": "Remote",
        "link": "https://example.test/jobs/1",
        "skills": [],
        "salary_raw": None,
        "salary_numeric": None,
    }
    values.update(overrides)
    return Job(**values)


def test_analyze_worker_normalizes_salary_and_backfills_skills() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        session.add(_job(salary_raw="15k per month"))
        session.commit()

        result = run(session)
        stored = session.query(Job).one()

    engine.dispose()

    assert result.jobs_processed == 1
    assert result.salary_normalized == 1
    assert result.skills_backfilled == 1
    assert stored.salary_numeric == 15_000
    assert stored.skills == ["python"]


def test_analyze_worker_skips_jobs_already_normalized() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        session.add(
            _job(salary_raw="15k per month", salary_numeric=15_000, skills=["python"])
        )
        session.commit()

        result = run(session)

    engine.dispose()

    assert result.salary_normalized == 0
    assert result.skills_backfilled == 0


def test_analyze_worker_leaves_unrecognized_salary_and_skills_untouched() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        session.add(_job(salary_raw="unpaid", title="Growth Intern"))
        session.commit()

        result = run(session)
        stored = session.query(Job).one()

    engine.dispose()

    assert result.salary_normalized == 0
    assert result.skills_backfilled == 0
    assert stored.salary_numeric is None
    assert stored.skills == []
