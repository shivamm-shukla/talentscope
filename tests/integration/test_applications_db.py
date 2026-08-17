import pytest

from db.applications import get_or_create, list_for_user, set_status, statuses_by_job_id
from db.models import Base, Job, User
from db.session import create_engine_and_session


def make_job(**overrides) -> Job:
    values = {
        "source": "internshala",
        "title": "Backend Intern",
        "company": "Acme",
        "location": "Remote",
        "skills": ["python"],
        "link": "https://internshala.test/job/1",
    }
    values.update(overrides)
    return Job(**values)


def test_get_or_create_starts_at_saved_with_history() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        job = make_job()
        session.add_all([user, job])
        session.commit()

        application = get_or_create(session, user, job)
        session.commit()

        assert application.status == "saved"
        assert [h["status"] for h in application.status_history] == ["saved"]
    engine.dispose()


def test_get_or_create_is_idempotent_per_user_job() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        job = make_job()
        session.add_all([user, job])
        session.commit()

        first = get_or_create(session, user, job)
        session.commit()
        second = get_or_create(session, user, job)
        session.commit()

        assert first.id == second.id
    engine.dispose()


def test_set_status_appends_history_and_stamps_applied_at() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        job = make_job()
        session.add_all([user, job])
        session.commit()
        application = get_or_create(session, user, job)
        session.commit()

        set_status(session, application, "applied")
        session.commit()

        assert application.status == "applied"
        assert application.applied_at is not None
        assert [h["status"] for h in application.status_history] == ["saved", "applied"]
    engine.dispose()


def test_set_status_rejects_unknown_status() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        job = make_job()
        session.add_all([user, job])
        session.commit()
        application = get_or_create(session, user, job)
        session.commit()

        with pytest.raises(ValueError):
            set_status(session, application, "ghosted")
    engine.dispose()


def test_statuses_by_job_id_and_list_for_user() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        job = make_job()
        session.add_all([user, job])
        session.commit()
        application = get_or_create(session, user, job, status="applied")
        session.commit()

        assert statuses_by_job_id(session, user) == {job.id: "applied"}
        assert [a.id for a in list_for_user(session, user)] == [application.id]
    engine.dispose()
