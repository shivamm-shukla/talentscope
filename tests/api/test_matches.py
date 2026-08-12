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
    app.extensions["talentscope_engine"].dispose()


def signup(client):
    return client.post(
        "/auth/signup",
        json={"email": "student@example.test", "password": "password123"},
    )


def seed_match(app, *, score=80, reasons=("matches python",)):
    session_factory = app.extensions["talentscope_session_factory"]
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
