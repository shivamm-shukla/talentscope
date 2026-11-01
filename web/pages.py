"""Server-rendered HTML pages for the Santa web frontend.

Every page is reachable without an account: guests browse the feed, open
postings and see market insights. Pages fetch their data from the JSON API
and ask for sign-in (an inline modal, see static/js/app.js) only at the
moment an action needs an account — so no page here redirects to login.
"""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

pages = Blueprint("pages", __name__)


@pages.get("/")
def index():
    return render_template("index.html")


@pages.get("/signup")
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return render_template("signup.html")


@pages.get("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html")


@pages.get("/welcome")
def welcome():
    return render_template("welcome.html")


@pages.get("/app")
def dashboard():
    return render_template("dashboard.html", active="home")


@pages.get("/app/jobs/<int:job_id>")
def job_page(job_id: int):
    return render_template("job.html", active="home", job_id=job_id)


@pages.get("/app/applications")
def applications_page():
    return render_template("applications.html", active="applications")


@pages.get("/app/insights")
def insights_page():
    return render_template("insights.html", active="insights")


@pages.get("/app/preferences")
def preferences_page():
    return render_template("preferences.html", active="preferences")


@pages.get("/app/ask")
def ask_page():
    return render_template("ask.html", active="ask")


@pages.get("/app/resume")
def resume_page():
    return render_template("resume.html", active="resume")
