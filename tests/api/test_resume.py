import pytest

from web import create_app


def fake_generate(prompt: str) -> str:
    return "GENERATED RESUME TEXT"


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
            "CREATE_DATABASE": True,
            "RESUME_GENERATE_FN": fake_generate,
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


def test_resume_generate_requires_login(client) -> None:
    response = client.post("/resume/generate")

    assert response.status_code == 401


def test_resume_generate_with_no_synced_profile_still_succeeds(client) -> None:
    signup(client)

    response = client.post("/resume/generate")

    assert response.status_code == 201
    body = response.get_json()
    assert body["version"] == 1
    assert body["is_final"] is False
    assert body["content"] == "GENERATED RESUME TEXT"
    assert body["sections"]["skills"]["bullets"] == []


def test_edit_and_finalize_a_draft(client) -> None:
    signup(client)
    draft = client.post("/resume/generate").get_json()

    edited = client.patch(
        f"/resume/{draft['id']}",
        json={"sections": {"skills": {"heading": "Skills", "bullets": ["Python"]}}},
    ).get_json()
    assert edited["sections"]["skills"]["bullets"] == ["Python"]
    assert edited["is_final"] is False

    finalized = client.post(f"/resume/{draft['id']}/finalize").get_json()
    assert finalized["is_final"] is True


def test_cannot_edit_a_finalized_version(client) -> None:
    signup(client)
    draft = client.post("/resume/generate").get_json()
    client.post(f"/resume/{draft['id']}/finalize")

    response = client.patch(
        f"/resume/{draft['id']}",
        json={"sections": {"skills": {"heading": "Skills", "bullets": ["Python"]}}},
    )

    assert response.status_code == 409


def test_second_generate_call_creates_version_two(client) -> None:
    signup(client)
    client.post("/resume/generate")

    second = client.post("/resume/generate").get_json()

    assert second["version"] == 2
    versions = client.get("/resume").get_json()
    assert [v["version"] for v in versions] == [2, 1]


def test_resume_routes_are_scoped_to_the_owning_user(client) -> None:
    signup(client)
    draft = client.post("/resume/generate").get_json()
    client.post("/auth/logout")
    client.post(
        "/auth/signup",
        json={"email": "other@example.test", "password": "password123"},
    )

    response = client.patch(f"/resume/{draft['id']}", json={"sections": {}})

    assert response.status_code == 404
