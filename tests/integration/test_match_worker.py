from db.models import Base, Job, Match, User, UserPreference
from db.session import create_engine_and_session
from workers.run_match import run


def test_match_worker_records_and_refreshes_matches() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        user.preferences = UserPreference(skills=["python"], locations=["Remote"])
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

        first = run(session)
        second = run(session)
        stored = session.query(Match).one()

    engine.dispose()

    assert first.created == 1 and first.updated == 0
    assert second.created == 0 and second.updated == 1
    assert stored.score == 100
    assert stored.reasons == ["skills: python", "location: Remote"]
