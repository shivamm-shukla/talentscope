import pytest

from db.models import Job
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


def seed_job(app) -> int:
    session_factory = app.extensions["santa_session_factory"]
    with session_factory() as session:
        job = Job(
            source="internshala",
            title="Backend Intern",
            company="Acme",
            location="Remote",
            skills=["python"],
            link="https://internshala.test/job/1",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def test_applications_require_login(client) -> None:
    assert client.get("/applications").status_code == 401
    assert client.post("/applications", json={"job_id": 1}).status_code == 401


def test_create_application_defaults_to_saved(client) -> None:
    signup(client)
    job_id = seed_job(client.application)

    response = client.post("/applications", json={"job_id": job_id})

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "saved"
    assert body["job"]["title"] == "Backend Intern"


def test_create_application_rejects_unknown_job(client) -> None:
    signup(client)

    response = client.post("/applications", json={"job_id": 999})

    assert response.status_code == 404


def test_create_application_rejects_unknown_status(client) -> None:
    signup(client)
    job_id = seed_job(client.application)

    response = client.post(
        "/applications", json={"job_id": job_id, "status": "ghosted"}
    )

    assert response.status_code == 400


def test_update_application_status_and_notes(client) -> None:
    signup(client)
    job_id = seed_job(client.application)
    created = client.post("/applications", json={"job_id": job_id}).get_json()

    response = client.patch(
        f"/applications/{created['id']}",
        json={"status": "applied", "notes": "Referred by a friend"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "applied"
    assert body["notes"] == "Referred by a friend"
    assert body["applied_at"] is not None


def test_applications_are_scoped_to_the_owning_user(client) -> None:
    signup(client)
    job_id = seed_job(client.application)
    created = client.post("/applications", json={"job_id": job_id}).get_json()
    client.post("/auth/logout")
    client.post(
        "/auth/signup",
        json={"email": "other@example.test", "password": "password123"},
    )

    response = client.patch(
        f"/applications/{created['id']}", json={"status": "applied"}
    )

    assert response.status_code == 404


def test_list_applications(client) -> None:
    signup(client)
    job_id = seed_job(client.application)
    client.post("/applications", json={"job_id": job_id})

    response = client.get("/applications")

    assert response.status_code == 200
    [application] = response.get_json()
    assert application["job_id"] == job_id


def test_matches_includes_application_status(client) -> None:
    signup(client)
    app = client.application
    session_factory = app.extensions["santa_session_factory"]
    from db.models import Match, User

    with session_factory() as session:
        user = session.query(User).one()
        job = Job(
            source="internshala",
            title="Backend Intern",
            company="Acme",
            location="Remote",
            skills=["python"],
            link="https://internshala.test/job/1",
        )
        session.add(job)
        session.flush()
        session.add(Match(user_id=user.id, job_id=job.id, score=80, reasons=[]))
        session.commit()
        job_id = job.id

    client.post("/applications", json={"job_id": job_id, "status": "applied"})

    response = client.get("/matches")

    [match] = response.get_json()
    assert match["application_status"] == "applied"
    assert match["job"]["id"] == job_id


def test_applications_stats_requires_login(client) -> None:
    assert client.get("/applications/stats").status_code == 401


def test_applications_stats_reflects_tracked_progress(client) -> None:
    signup(client)
    job_id = seed_job(client.application)
    created = client.post(
        "/applications", json={"job_id": job_id, "status": "applied"}
    ).get_json()
    client.patch(f"/applications/{created['id']}", json={"status": "interviewing"})

    response = client.get("/applications/stats")

    assert response.status_code == 200
    body = response.get_json()
    assert body["applications_tracked"] == 1
    assert body["applied_count"] == 1
    assert body["response_count"] == 1
    assert body["response_rate"] == 1.0
    assert body["offer_count"] == 0
