"""Without GEMINI_API_KEY every AI feature answers 503 with a plain reason,
instead of a generic 502 that hides why nothing works."""

import pytest

from db.models import Job
from web import create_app
from web.routes import AI_UNAVAILABLE_MESSAGE


@pytest.fixture
def client(tmp_path, monkeypatch):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
            "CREATE_DATABASE": True,
        }
    )
    # After create_app: it loads .env, and a developer's real key must not
    # leak into this test.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with app.test_client() as test_client:
        test_client.post(
            "/auth/signup",
            json={"email": "student@example.test", "password": "password123"},
        )
        yield test_client
    app.extensions["santa_engine"].dispose()


def seed_job(app) -> int:
    with app.extensions["santa_session_factory"]() as session:
        job = Job(
            source="internshala",
            title="Backend Intern",
            company="Acme",
            location="Remote",
            link="https://internshala.test/job/1",
        )
        session.add(job)
        session.commit()
        return job.id


def test_qa_reports_missing_ai_configuration(client) -> None:
    response = client.post("/qa", json={"question": "What's trending?"})

    assert response.status_code == 503
    assert response.get_json()["error"] == AI_UNAVAILABLE_MESSAGE


def test_company_brief_reports_missing_ai_configuration(client) -> None:
    job_id = seed_job(client.application)

    response = client.get(f"/jobs/{job_id}/brief")

    assert response.status_code == 503
    assert response.get_json()["error"] == AI_UNAVAILABLE_MESSAGE


def test_resume_reports_missing_ai_configuration(client) -> None:
    response = client.post("/resume/generate")

    assert response.status_code == 503
    assert response.get_json()["error"] == AI_UNAVAILABLE_MESSAGE
