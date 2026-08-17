import pytest

from db.models import Job
from web import create_app


def fake_generate(prompt: str) -> str:
    return "Acme is a fictional software company that builds internal tools."


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
            "CREATE_DATABASE": True,
            "GENERATE_FN": fake_generate,
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


def seed_job(app, **overrides) -> int:
    session_factory = app.extensions["santa_session_factory"]
    values = {
        "source": "internshala",
        "title": "Backend Intern",
        "company": "Acme",
        "location": "Remote",
        "skills": ["python"],
        "description": "Acme builds internal developer tools.",
        "link": "https://internshala.test/job/1",
    }
    values.update(overrides)
    with session_factory() as session:
        job = Job(**values)
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def test_job_brief_requires_login(client) -> None:
    assert client.get("/jobs/1/brief").status_code == 401


def test_job_brief_404s_for_unknown_job(client) -> None:
    signup(client)

    assert client.get("/jobs/999/brief").status_code == 404


def test_job_brief_generates_and_caches(client) -> None:
    signup(client)
    job_id = seed_job(client.application)

    response = client.get(f"/jobs/{job_id}/brief")

    assert response.status_code == 201
    body = response.get_json()
    assert body["company"] == "Acme"
    assert body["cached"] is False
    assert "software" in body["content"]


def test_job_brief_is_cached_on_second_request(client) -> None:
    signup(client)
    job_id = seed_job(client.application)
    client.get(f"/jobs/{job_id}/brief")

    response = client.get(f"/jobs/{job_id}/brief")

    assert response.status_code == 200
    assert response.get_json()["cached"] is True


def test_job_brief_shared_across_jobs_at_the_same_company(client) -> None:
    signup(client)
    app = client.application
    first_job_id = seed_job(app, title="Backend Intern")
    second_job_id = seed_job(
        app, title="Frontend Intern", link="https://internshala.test/job/2"
    )

    client.get(f"/jobs/{first_job_id}/brief")
    response = client.get(f"/jobs/{second_job_id}/brief")

    assert response.status_code == 200
    assert response.get_json()["cached"] is True
