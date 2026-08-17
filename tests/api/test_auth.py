import io
import zipfile

import pytest

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


def test_signup_logs_in_user_and_prevents_duplicates(client) -> None:
    response = signup(client)

    assert response.status_code == 201
    assert client.get("/auth/me").get_json() == {
        "id": 1,
        "email": "student@example.test",
    }
    assert signup(client).status_code == 409


def test_login_logout_and_preference_crud(client) -> None:
    signup(client)
    assert client.post("/auth/logout").status_code == 204
    assert (
        client.post(
            "/auth/login",
            json={"email": "student@example.test", "password": "password123"},
        ).status_code
        == 200
    )

    saved = client.put(
        "/preferences",
        json={
            "skills": ["python"],
            "locations": ["Remote"],
            "minimum_stipend": 12000,
            "channels": ["email", "telegram"],
            "telegram_chat_id": "1333041980",
            "github_username": "octocat",
        },
    )

    assert saved.status_code == 200
    assert client.get("/preferences").get_json() == {
        "skills": ["python"],
        "locations": ["Remote"],
        "minimum_stipend": 12000,
        "channels": ["email", "telegram"],
        "telegram_chat_id": "1333041980",
        "github_username": "octocat",
        "github_profile": None,
        "linkedin_profile": None,
    }


def test_protected_routes_require_login(client) -> None:
    assert client.get("/preferences").status_code == 401


def _linkedin_export_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Skills.csv", "Name\nPython\nSQL\n")
    return buffer.getvalue()


def test_linkedin_import_updates_skills_and_profile_status(client) -> None:
    signup(client)

    response = client.post(
        "/preferences/linkedin-import",
        data={"export": (io.BytesIO(_linkedin_export_zip()), "export.zip")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["skill_count"] == 2

    prefs = client.get("/preferences").get_json()
    assert prefs["skills"] == ["Python", "SQL"]
    assert prefs["linkedin_profile"]["skill_count"] == 2


def test_linkedin_import_rejects_non_zip_upload(client) -> None:
    signup(client)

    response = client.post(
        "/preferences/linkedin-import",
        data={"export": (io.BytesIO(b"not a zip"), "export.zip")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
