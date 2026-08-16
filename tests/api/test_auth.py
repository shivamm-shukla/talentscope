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
    app.extensions["talentscope_engine"].dispose()


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
        },
    )

    assert saved.status_code == 200
    assert client.get("/preferences").get_json() == {
        "skills": ["python"],
        "locations": ["Remote"],
        "minimum_stipend": 12000,
        "channels": ["email", "telegram"],
        "telegram_chat_id": "1333041980",
    }


def test_protected_routes_require_login(client) -> None:
    assert client.get("/preferences").status_code == 401
