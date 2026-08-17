"""JSON routes for authentication, preference management, and Q&A."""

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.registry import create_generate_fn, create_qa_engine
from ai.resume_prompt import generate_resume_content
from analysis.linkedin_skills import infer_skills as infer_linkedin_skills
from analysis.resume_builder import build_resume_draft
from auth.passwords import hash_password, verify_password
from core.interfaces import QAEngine
from core.models import JobPosting, QueryContext
from core.models import User as DomainUser
from db.applications import get_or_create as get_or_create_application
from db.applications import list_for_user as list_applications_for_user
from db.applications import set_status as set_application_status
from db.applications import statuses_by_job_id
from db.linkedin_profiles import upsert_linkedin_profile
from db.models import (
    APPLICATION_STATUSES,
    Application,
    GithubProfile,
    Job,
    LinkedinProfile,
    Match,
    ResumeDocument,
    User,
    UserPreference,
)
from db.preferences import merge_inferred_skills_into_preferences
from db.resume_documents import (
    create_draft,
    finalize,
    list_versions,
    update_draft_sections,
)
from integrations.linkedin.parser import (
    LinkedinExportInvalid,
    LinkedinExportTooLarge,
    parse_export,
)

api = Blueprint("api", __name__)


def _session() -> Session:
    return current_app.extensions["santa_session_factory"]()


def _qa_engine() -> QAEngine:
    override = current_app.config.get("QA_ENGINE")
    if override is not None:
        return override
    if "santa_qa_engine" not in current_app.extensions:
        current_app.extensions["santa_qa_engine"] = create_qa_engine()
    return current_app.extensions["santa_qa_engine"]


def _generate_fn():
    override = current_app.config.get("RESUME_GENERATE_FN")
    if override is not None:
        return override
    if "santa_generate_fn" not in current_app.extensions:
        current_app.extensions["santa_generate_fn"] = create_generate_fn()
    return current_app.extensions["santa_generate_fn"]


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


def _github_payload(profile: GithubProfile | None) -> dict[str, object] | None:
    if profile is None:
        return None
    return {
        "repo_count": profile.repo_count,
        "languages": profile.languages,
        "synced_at": profile.synced_at.isoformat(),
    }


def _linkedin_payload(profile: LinkedinProfile | None) -> dict[str, object] | None:
    if profile is None:
        return None
    return {
        "headline": profile.headline,
        "position_count": len(profile.positions),
        "skill_count": len(profile.inferred_skills),
        "synced_at": profile.synced_at.isoformat(),
    }


def _preference_payload(
    preferences: UserPreference | None,
    telegram_chat_id: str | None,
    github_username: str | None,
    github_profile: GithubProfile | None,
    linkedin_profile: LinkedinProfile | None,
) -> dict[str, object]:
    base = {
        "skills": [],
        "locations": [],
        "minimum_stipend": None,
        "channels": [],
        "telegram_chat_id": telegram_chat_id,
        "github_username": github_username,
        "github_profile": _github_payload(github_profile),
        "linkedin_profile": _linkedin_payload(linkedin_profile),
    }
    if preferences is None:
        return base
    return {
        **base,
        "skills": preferences.skills,
        "locations": preferences.locations,
        "minimum_stipend": preferences.minimum_stipend,
        "channels": preferences.preferred_channels,
    }


def _application_payload(application: Application) -> dict[str, object]:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "status": application.status,
        "status_history": application.status_history,
        "applied_at": (
            application.applied_at.isoformat() if application.applied_at else None
        ),
        "notes": application.notes,
        "updated_at": application.updated_at.isoformat(),
        "job": {
            "title": application.job.title,
            "company": application.job.company,
            "location": application.job.location,
            "link": application.job.link,
        },
    }


def _resume_payload(resume: ResumeDocument) -> dict[str, object]:
    return {
        "id": resume.id,
        "version": resume.version,
        "content": resume.content,
        "sections": resume.sections,
        "is_final": resume.is_final,
        "generated_at": resume.generated_at.isoformat(),
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
        login_user(user, remember=True)
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
        login_user(user, remember=True)
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
            return jsonify(
                _preference_payload(
                    user.preferences,
                    user.telegram_chat_id,
                    user.github_username,
                    user.github_profile,
                    user.linkedin_profile,
                )
            )
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
        if "github_username" in payload:
            value = payload["github_username"]
            if value is not None and not isinstance(value, str):
                return jsonify(error="github_username must be a string"), 400
            user.github_username = value
        session.commit()
        return jsonify(
            _preference_payload(
                preference,
                user.telegram_chat_id,
                user.github_username,
                user.github_profile,
                user.linkedin_profile,
            )
        )


@api.post("/preferences/linkedin-import")
@login_required
def linkedin_import():
    upload = request.files.get("export")
    if upload is None or not upload.filename:
        return jsonify(error="no file uploaded"), 400

    try:
        export = parse_export(upload.read())
    except LinkedinExportInvalid as error:
        return jsonify(error=str(error)), 400
    except LinkedinExportTooLarge as error:
        return jsonify(error=str(error)), 400

    inferred = infer_linkedin_skills(export)
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        merge_inferred_skills_into_preferences(session, user, inferred)
        profile = upsert_linkedin_profile(session, user, export, inferred)
        session.commit()
        return jsonify(_linkedin_payload(profile))


@api.get("/matches")
@login_required
def matches():
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        rows = session.scalars(
            select(Match)
            .where(Match.user_id == current_user.id)
            .join(Match.job)
            .order_by(Match.score.desc())
        ).all()
        application_status_by_job = statuses_by_job_id(session, user)
        return jsonify(
            [
                {
                    "score": match.score,
                    "reasons": match.reasons,
                    "matched_at": match.matched_at.isoformat(),
                    "application_status": application_status_by_job.get(match.job_id),
                    "job": {
                        "id": match.job.id,
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
                        "quality_flags": match.job.quality_flags,
                    },
                }
                for match in rows
            ]
        )


QA_CONTEXT_JOB_LIMIT = 50


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
        rows = session.scalars(
            select(Job).order_by(Job.scraped_at.desc()).limit(QA_CONTEXT_JOB_LIMIT)
        ).all()
        jobs = tuple(_job_posting(job) for job in rows)

    context = QueryContext(user=domain_user, jobs=jobs)
    try:
        answer = _qa_engine().answer(question, context)
    except Exception:
        current_app.logger.exception("QA engine failed to answer question")
        return jsonify(error="unable to answer question right now"), 502
    return jsonify(text=answer.text, sources=list(answer.sources))


@api.get("/applications")
@login_required
def applications_list():
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        applications = list_applications_for_user(session, user)
        return jsonify([_application_payload(a) for a in applications])


@api.post("/applications")
@login_required
def applications_create():
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("job_id")
    status = payload.get("status", "saved")
    if not isinstance(job_id, int):
        return jsonify(error="job_id is required"), 400
    if status not in APPLICATION_STATUSES:
        return (
            jsonify(error=f"status must be one of {sorted(APPLICATION_STATUSES)}"),
            400,
        )
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        job = session.get(Job, job_id)
        if job is None:
            return jsonify(error="job not found"), 404
        application = get_or_create_application(session, user, job, status)
        session.commit()
        session.refresh(application)
        return jsonify(_application_payload(application)), 201


def _owned_application(session: Session, application_id: int) -> Application | None:
    application = session.get(Application, application_id)
    if application is None or application.user_id != current_user.id:
        return None
    return application


@api.patch("/applications/<int:application_id>")
@login_required
def applications_update(application_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    notes = payload.get("notes")
    if status is not None and status not in APPLICATION_STATUSES:
        return (
            jsonify(error=f"status must be one of {sorted(APPLICATION_STATUSES)}"),
            400,
        )
    if notes is not None and not isinstance(notes, str):
        return jsonify(error="notes must be a string"), 400
    with _session() as session:
        application = _owned_application(session, application_id)
        if application is None:
            return jsonify(error="application not found"), 404
        if status is not None:
            set_application_status(session, application, status)
        if notes is not None:
            application.notes = notes
        session.commit()
        return jsonify(_application_payload(application))


@api.post("/resume/generate")
@login_required
def resume_generate():
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        github = user.github_profile
        linkedin = user.linkedin_profile
        skills = list(user.preferences.skills) if user.preferences else []
        sections = build_resume_draft(
            skills=skills,
            headline=linkedin.headline if linkedin else "",
            positions=linkedin.positions if linkedin else [],
            education=linkedin.education if linkedin else [],
            certifications=linkedin.certifications if linkedin else [],
            languages=github.languages if github else [],
            repo_count=github.repo_count if github else 0,
        )
        try:
            content = generate_resume_content(
                _generate_fn(), user.name or user.email, sections
            )
        except Exception:
            current_app.logger.exception("resume generation failed")
            return jsonify(error="unable to generate resume right now"), 502

        source_snapshot = {
            "github_synced_at": github.synced_at.isoformat() if github else None,
            "linkedin_synced_at": linkedin.synced_at.isoformat() if linkedin else None,
            "skills": skills,
        }
        resume = create_draft(session, user, content, sections, source_snapshot)
        session.commit()
        session.refresh(resume)
        return jsonify(_resume_payload(resume)), 201


@api.get("/resume")
@login_required
def resume_list():
    with _session() as session:
        user = session.get(User, current_user.id)
        assert user is not None
        versions = list_versions(session, user)
        return jsonify([_resume_payload(resume) for resume in versions])


def _owned_resume(session: Session, resume_id: int) -> ResumeDocument | None:
    resume = session.get(ResumeDocument, resume_id)
    if resume is None or resume.user_id != current_user.id:
        return None
    return resume


@api.patch("/resume/<int:resume_id>")
@login_required
def resume_edit(resume_id: int):
    payload = request.get_json(silent=True) or {}
    sections = payload.get("sections")
    if not isinstance(sections, dict):
        return jsonify(error="sections must be an object"), 400
    with _session() as session:
        resume = _owned_resume(session, resume_id)
        if resume is None:
            return jsonify(error="resume not found"), 404
        try:
            update_draft_sections(session, resume, sections)
        except ValueError as error:
            return jsonify(error=str(error)), 409
        session.commit()
        return jsonify(_resume_payload(resume))


@api.post("/resume/<int:resume_id>/finalize")
@login_required
def resume_finalize(resume_id: int):
    with _session() as session:
        resume = _owned_resume(session, resume_id)
        if resume is None:
            return jsonify(error="resume not found"), 404
        finalize(session, resume)
        session.commit()
        return jsonify(_resume_payload(resume))
