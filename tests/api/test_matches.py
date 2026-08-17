from datetime import UTC, datetime

import pytest

from db.models import Job, Match, User
from web import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
            "CREATE_DATABASE": True,
        }
    )
    with app.test_client() as test_client:
        yield test_client
    app.extensions["santa_engine"].dispose()


def signup(client):
    return client.post(
        "/auth/signup",
        json={"email": "student@example.test", "password": "password123"},
    )


def seed_match(app, *, score=80, reasons=("matches python",), deadline_at=None):
    session_factory = app.extensions["santa_session_factory"]
    with session_factory() as session:
        user = session.query(User).one()
        job = Job(
            source="internshala",
            title="Backend Intern",
            company="Acme",
            location="Remote",
            salary_raw="₹15,000/month",
            skills=["python"],
            link="https://internshala.test/job/1",
            deadline_at=deadline_at,
        )
        session.add(job)
        session.flush()
        session.add(
            Match(user_id=user.id, job_id=job.id, score=score, reasons=list(reasons))
        )
        session.commit()


def test_matches_returns_ranked_jobs_for_current_user(client) -> None:
    app = client.application
    signup(client)
    seed_match(app)

    response = client.get("/matches")

    assert response.status_code == 200
    [match] = response.get_json()
    assert match["score"] == 80
    assert match["reasons"] == ["matches python"]
    assert match["job"]["title"] == "Backend Intern"
    assert match["job"]["company"] == "Acme"


def test_matches_requires_login(client) -> None:
    assert client.get("/matches").status_code == 401


def test_matches_includes_deadline_at_when_known(client) -> None:
    app = client.application
    signup(client)
    deadline = datetime(2026, 9, 16, 23, 59, 59, tzinfo=UTC)
    seed_match(app, deadline_at=deadline)

    [match] = client.get("/matches").get_json()

    assert match["job"]["deadline_at"] is not None
    assert match["job"]["deadline_at"].startswith("2026-09-16")


def test_matches_deadline_at_is_null_when_unknown(client) -> None:
    app = client.application
    signup(client)
    seed_match(app)

    [match] = client.get("/matches").get_json()

    assert match["job"]["deadline_at"] is None
