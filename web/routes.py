"""JSON routes for authentication and preference management."""

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.passwords import hash_password, verify_password
from db.models import User, UserPreference

api = Blueprint("api", __name__)


def _session() -> Session:
    return current_app.extensions["talentscope_session_factory"]()


def _preference_payload(preferences: UserPreference | None) -> dict[str, object]:
    if preferences is None:
        return {"skills": [], "locations": [], "minimum_stipend": None, "channels": []}
    return {
        "skills": preferences.skills,
        "locations": preferences.locations,
        "minimum_stipend": preferences.minimum_stipend,
        "channels": preferences.preferred_channels,
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
            return jsonify(_preference_payload(user.preferences))
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
        session.commit()
        return jsonify(_preference_payload(preference))
