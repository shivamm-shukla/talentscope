import pytest
from sqlalchemy.exc import IntegrityError

from db.models import Base, Job, Match, User, UserPreference
from db.session import create_engine_and_session


@pytest.fixture
def session():
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as database_session:
        yield database_session
    engine.dispose()


def make_job() -> Job:
    return Job(
        source="remotive",
        title="Python Intern",
        company="Example Co",
        location="Remote",
        link="https://example.test/jobs/1",
    )


def test_job_identity_is_unique(session) -> None:
    session.add_all([make_job(), make_job()])

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_user_cascades_preferences_and_matches(session) -> None:
    user = User(email="student@example.test", password_hash="hash")
    user.preferences = UserPreference(skills=["python"])
    user.matches.append(Match(job=make_job(), score=80, reasons=["python"]))
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    assert session.query(User).count() == 0
    assert session.query(UserPreference).count() == 0
    assert session.query(Match).count() == 0
