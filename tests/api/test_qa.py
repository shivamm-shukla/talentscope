import pytest

from core.models import Answer
from web import create_app


class FakeQAEngine:
    def __init__(self, answer: Answer) -> None:
        self._answer = answer
        self.calls = []

    def answer(self, question, context):
        self.calls.append((question, context))
        return self._answer


@pytest.fixture
def fake_engine():
    return FakeQAEngine(
        Answer(text="2 Python internships are open.", sources=("https://x.test/1",))
    )


@pytest.fixture
def client(tmp_path, fake_engine):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
            "CREATE_DATABASE": True,
            "QA_ENGINE": fake_engine,
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


def test_qa_requires_login(client) -> None:
    response = client.post("/qa", json={"question": "any jobs?"})

    assert response.status_code == 401


def test_qa_returns_fake_engine_answer(client, fake_engine) -> None:
    signup(client)

    response = client.post("/qa", json={"question": "any Python jobs?"})

    assert response.status_code == 200
    assert response.get_json() == {
        "text": "2 Python internships are open.",
        "sources": ["https://x.test/1"],
    }
    assert fake_engine.calls[0][0] == "any Python jobs?"


def test_qa_rejects_missing_question(client) -> None:
    signup(client)

    response = client.post("/qa", json={})

    assert response.status_code == 400
