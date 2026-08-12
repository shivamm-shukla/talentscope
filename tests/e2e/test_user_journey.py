"""End-to-end journey: signup, set preferences, and see matched jobs.

Runs the real Flask app behind a live WSGI server and drives it over HTTP with
Playwright's request API, exercising the full stack (routing, session cookies,
SQLite persistence) rather than the Flask test client used by the API layer.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest
from flask import Flask
from werkzeug.serving import BaseWSGIServer, make_server

from db.models import Job, Match, User
from web import create_app


@pytest.fixture
def live_server(tmp_path) -> Iterator[tuple[Flask, str]]:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'e2e.db'}",
            "CREATE_DATABASE": True,
        }
    )
    server: BaseWSGIServer = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield app, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        app.extensions["talentscope_engine"].dispose()


def seed_match_for(app: Flask, email: str) -> None:
    session_factory = app.extensions["talentscope_session_factory"]
    with session_factory() as session:
        user = session.query(User).filter_by(email=email).one()
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
            Match(user_id=user.id, job_id=job.id, score=90, reasons=["matches python"])
        )
        session.commit()


def test_signup_set_preferences_and_see_matched_jobs(live_server, playwright) -> None:
    app, base_url = live_server
    email = "student@example.test"
    request_context = playwright.request.new_context(base_url=base_url)
    try:
        signup = request_context.post(
            "/auth/signup", data={"email": email, "password": "password123"}
        )
        assert signup.ok
        assert signup.json()["email"] == email

        preferences = request_context.put(
            "/preferences",
            data={
                "skills": ["python"],
                "locations": ["Remote"],
                "minimum_stipend": 10000,
                "channels": ["email"],
            },
        )
        assert preferences.ok
        assert preferences.json()["skills"] == ["python"]

        # The matching pipeline runs out-of-band (workers/match.py); seed its
        # output directly rather than re-running that worker in this test.
        seed_match_for(app, email)

        matches = request_context.get("/matches")
        assert matches.ok
        [match] = matches.json()
        assert match["job"]["title"] == "Backend Intern"
        assert match["score"] == 90
    finally:
        request_context.dispose()
