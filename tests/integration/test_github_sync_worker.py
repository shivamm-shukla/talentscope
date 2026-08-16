from core.models import GithubRepo
from db.models import Base, User, UserPreference
from db.session import create_engine_and_session
from workers.run_github_sync import run


def repo(**overrides) -> GithubRepo:
    values = {
        "name": "job-matcher",
        "description": "A Flask app.",
        "language": "Python",
        "topics": (),
    }
    values.update(overrides)
    return GithubRepo(**values)


def test_github_sync_merges_inferred_skills_and_stores_snapshot() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        user = User(
            email="student@example.test", password_hash="hash", github_username="octo"
        )
        user.preferences = UserPreference(skills=["sql"])
        session.add(user)
        session.commit()

        result = run(session, fetch=lambda _username: [repo()])
        session.refresh(user)

        assert (result.users_synced, result.skills_added, result.failed) == (1, 2, 0)
        assert user.preferences.skills == ["sql", "python", "flask"]
        assert user.github_profile.repo_count == 1
        assert user.github_profile.languages == ["Python"]

    engine.dispose()


def test_github_sync_isolates_per_user_failures() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        failing = User(
            email="broken@example.test", password_hash="hash", github_username="ghost"
        )
        working = User(
            email="ok@example.test", password_hash="hash", github_username="octo"
        )
        session.add_all([failing, working])
        session.commit()

        def fetch(username: str) -> list[GithubRepo]:
            if username == "ghost":
                raise RuntimeError("404")
            return [repo()]

        result = run(session, fetch=fetch)
        session.refresh(working)

        assert result.users_synced == 1
        assert result.failed == 1
        assert working.github_profile is not None

    engine.dispose()
