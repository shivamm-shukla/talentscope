"""Server-rendered HTML pages for the Santa web frontend."""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

pages = Blueprint("pages", __name__)


def login_required_page(view):
    """Redirect anonymous visitors to the login page (unlike the JSON API,
    which returns 401 so `flask_login`'s default unauthorized handler stays
    untouched for `web.routes`)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("pages.login_page"))
        return view(*args, **kwargs)

    return wrapped


@pages.get("/")
def index():
    return render_template("index.html")


@pages.get("/signup")
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("pages.feed"))
    return render_template("signup.html")


@pages.get("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("pages.feed"))
    return render_template("login.html")


@pages.get("/app")
@login_required_page
def feed():
    return render_template("feed.html")


@pages.get("/app/preferences")
@login_required_page
def preferences_page():
    return render_template("preferences.html")


@pages.get("/app/ask")
@login_required_page
def ask_page():
    return render_template("ask.html")


@pages.get("/app/resume")
@login_required_page
def resume_page():
    return render_template("resume.html")
