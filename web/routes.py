"""JSON routes for authentication, preference management, and Q&A."""

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.registry import create_qa_engine
from auth.passwords import hash_password, verify_password
from core.interfaces import QAEngine
from core.models import JobPosting, QueryContext
from core.models import User as DomainUser
from db.models import Job, Match, User, UserPreference

api = Blueprint("api", __name__)


def _session() -> Session:
    return current_app.extensions["talentscope_session_factory"]()


def _qa_engine() -> QAEngine:
    override = current_app.config.get("QA_ENGINE")
    if override is not None:
        return override
    if "talentscope_qa_engine" not in current_app.extensions:
        current_app.extensions["talentscope_qa_engine"] = create_qa_engine()
    return current_app.extensions["talentscope_qa_engine"]


def _job_posting(job: Job) -> JobPosting:
    return JobPosting(
        source=job.source,
        title=job.title,
        company=job.company,
        location=job.location,
        link=job.link,
        posted_at=job.posted_at,
        scraped_at=job.scraped_at,
        salary_raw=job.salary_raw,
        salary_numeric=job.salary_numeric,
        skills=tuple(job.skills),
        listing_type=job.listing_type,
        work_mode=job.work_mode,
        pay_type=job.pay_type,
        duration_months=job.duration_months,
        target_year=job.target_year,
        expires_at=job.expires_at,
    )


def _preference_payload(
    preferences: UserPreference | None, telegram_chat_id: str | None
) -> dict[str, object]:
    if preferences is None:
        return {
            "skills": [],
            "locations": [],
            "minimum_stipend": None,
            "channels": [],
            "telegram_chat_id": telegram_chat_id,
        }
    return {
        "skills": preferences.skills,
        "locations": preferences.locations,
        "minimum_stipend": preferences.minimum_stipend,
        "channels": preferences.preferred_channels,
        "telegram_chat_id": telegram_chat_id,
    }


@api.post("/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    email, password = payload.get("email"), payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or len(password) < 8:
        return jsonify(error="email and an 8-character password are required"), 400
    with _session() as session:
        if session.scalar(select(User).where(User.email == email.casefold())):
            return jsonify(error="email is already registered"), 409
        user = User(email=email.casefold(), password_hash=hash_password(password))
        session.add(user)
        session.commit()
        session.refresh(user)
        login_user(user)
        return jsonify(id=user.id, email=user.email), 201


@api.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email, password = payload.get("email"), payload.get("password")
    with _session() as session:
        user = session.scalar(select(User).where(User.email == str(email).casefold()))
        if (
            user is None
            or not isinstance(password, str)
            or not verify_password(password, user.password_hash)
        ):
            return jsonify(error="invalid email or password"), 401
        login_user(user)
        return jsonify(id=user.id, email=user.email)


@api.post("/auth/logout")
@login_required
def logout():
    logout_user()
    return "", 204


@api.get("/auth/me")
@login_required
def me():
    return jsonify(id=current_user.id, email=current_user.email)


@api.route("/preferences", methods=["GET", "PUT"])
@login_required
def preferences():
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        if request.method == "GET":
            return jsonify(_preference_payload(user.preferences, user.telegram_chat_id))
        payload = request.get_json(silent=True) or {}
        preference = user.preferences or UserPreference()
        if user.preferences is None:
            user.preferences = preference
        for key, attribute in (
            ("skills", "skills"),
            ("locations", "locations"),
            ("channels", "preferred_channels"),
        ):
            if key in payload:
                if not isinstance(payload[key], list) or not all(
                    isinstance(item, str) for item in payload[key]
                ):
                    return jsonify(error=f"{key} must be a list of strings"), 400
                setattr(preference, attribute, payload[key])
        if "minimum_stipend" in payload:
            value = payload["minimum_stipend"]
            if value is not None and (not isinstance(value, int) or value < 0):
                return (
                    jsonify(error="minimum_stipend must be a non-negative integer"),
                    400,
                )
            preference.minimum_stipend = value
        if "telegram_chat_id" in payload:
            value = payload["telegram_chat_id"]
            if value is not None and not isinstance(value, str):
                return jsonify(error="telegram_chat_id must be a string"), 400
            user.telegram_chat_id = value
        session.commit()
        return jsonify(_preference_payload(preference, user.telegram_chat_id))


@api.get("/matches")
@login_required
def matches():
    with _session() as session:
        rows = session.scalars(
            select(Match)
            .where(Match.user_id == current_user.id)
            .join(Match.job)
            .order_by(Match.score.desc())
        ).all()
        return jsonify(
            [
                {
                    "score": match.score,
                    "reasons": match.reasons,
                    "matched_at": match.matched_at.isoformat(),
                    "job": {
                        "title": match.job.title,
                        "company": match.job.company,
                        "location": match.job.location,
                        "link": match.job.link,
                        "salary_raw": match.job.salary_raw,
                        "skills": match.job.skills,
                        "listing_type": match.job.listing_type,
                        "work_mode": match.job.work_mode,
                        "pay_type": match.job.pay_type,
                        "duration_months": match.job.duration_months,
                        "target_year": match.job.target_year,
                    },
                }
                for match in rows
            ]
        )


@api.post("/qa")
@login_required
def qa():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify(error="question is required"), 400

    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        domain_user = DomainUser(id=user.id, email=user.email, name=user.name)
        jobs = tuple(_job_posting(job) for job in session.scalars(select(Job)).all())

    context = QueryContext(user=domain_user, jobs=jobs)
    try:
        answer = _qa_engine().answer(question, context)
    except Exception:
        current_app.logger.exception("QA engine failed to answer question")
        return jsonify(error="unable to answer question right now"), 502
    return jsonify(text=answer.text, sources=list(answer.sources))
