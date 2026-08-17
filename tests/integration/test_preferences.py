from db.models import Base, User, UserPreference
from db.preferences import merge_inferred_skills_into_preferences
from db.session import create_engine_and_session


def test_merge_creates_preferences_when_user_has_none() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        session.add(user)
        session.commit()

        preference = merge_inferred_skills_into_preferences(session, user, ["python"])
        session.commit()

        assert preference.skills == ["python"]
        assert user.preferences is preference
    engine.dispose()


def test_merge_unions_into_existing_preferences() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(email="student@example.test", password_hash="hash")
        user.preferences = UserPreference(skills=["SQL"])
        session.add(user)
        session.commit()

        preference = merge_inferred_skills_into_preferences(
            session, user, ["sql", "python"]
        )
        session.commit()

        assert preference.skills == ["SQL", "python"]
    engine.dispose()
