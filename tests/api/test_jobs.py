from datetime import UTC, datetime, timedelta

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


def signup(client, **extra):
    return client.post(
        "/auth/signup",
        json={"email": "student@example.test", "password": "password123", **extra},
    )


def seed_job(app, **overrides) -> int:
    fields = {
        "source": "internshala",
        "title": "Backend Intern",
        "company": "Acme",
        "location": "Bengaluru",
        "salary_numeric": 15_000,
        "skills": ["python", "sql"],
        "description": "Build APIs.",
        "link": "https://internshala.test/job/1",
        "listing_type": "internship",
        "posted_at": datetime.now(UTC) - timedelta(days=3),
        **overrides,
    }
    session_factory = app.extensions["santa_session_factory"]
    with session_factory() as session:
        job = Job(**fields)
        session.add(job)
        session.commit()
        return job.id


def test_jobs_feed_is_public_and_newest_first(client) -> None:
    app = client.application
    seed_job(app, title="Older", posted_at=datetime.now(UTC) - timedelta(days=9))
    seed_job(app, title="Newer", link="https://internshala.test/job/2")

    response = client.get("/jobs")

    assert response.status_code == 200
    titles = [item["job"]["title"] for item in response.get_json()]
    assert titles == ["Newer", "Older"]
    assert response.get_json()[0]["application_status"] is None


def test_jobs_feed_includes_application_status_when_logged_in(client) -> None:
    app = client.application
    job_id = seed_job(app)
    signup(client)
    client.post("/applications", json={"job_id": job_id, "status": "applied"})

    [item] = client.get("/jobs").get_json()

    assert item["application_status"] == "applied"


def test_job_detail_is_public_without_match_or_application(client) -> None:
    job_id = seed_job(client.application)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "Backend Intern"
    assert body["description"] == "Build APIs."
    assert body["match"] is None
    assert body["application"] is None


def test_job_detail_includes_match_and_application_for_owner(client) -> None:
    app = client.application
    job_id = seed_job(app)
    signup(client)
    with app.extensions["santa_session_factory"]() as session:
        user = session.query(User).one()
        session.add(Match(user_id=user.id, job_id=job_id, score=91, reasons=["x"]))
        session.commit()
    client.post("/applications", json={"job_id": job_id})

    body = client.get(f"/jobs/{job_id}").get_json()

    assert body["match"] == {"score": 91, "reasons": ["x"]}
    assert body["application"]["status"] == "saved"


def test_job_detail_404s_for_unknown_job(client) -> None:
    assert client.get("/jobs/999").status_code == 404


def test_trends_aggregates_recent_postings(client) -> None:
    app = client.application
    seed_job(app)
    seed_job(
        app,
        title="Data Intern",
        location="Pune",
        skills=["python"],
        salary_numeric=35_000,
        link="https://internshala.test/job/2",
    )
    seed_job(
        app,
        title="Stale",
        skills=["cobol"],
        posted_at=datetime.now(UTC) - timedelta(days=200),
        link="https://internshala.test/job/3",
    )

    body = client.get("/trends?days=90").get_json()

    assert body["total_jobs"] == 2
    assert body["skills"] == {"python": 2, "sql": 1}
    assert body["locations"] == {"Bengaluru": 1, "Pune": 1}
    assert body["stipends"]["10-20k"] == 1
    assert body["stipends"]["30-50k"] == 1


def test_trends_rejects_unsupported_period(client) -> None:
    assert client.get("/trends?days=7").status_code == 400


def test_signup_name_is_stored_and_editable(client) -> None:
    assert signup(client, name=" Aarav ").get_json()["name"] == "Aarav"

    client.put("/preferences", json={"name": "Aarav S"})

    assert client.get("/auth/me").get_json()["name"] == "Aarav S"
    assert client.put("/preferences", json={"name": 5}).status_code == 400
