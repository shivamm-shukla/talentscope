"""TalentScope Flask application factory."""

from __future__ import annotations

import os

from flask import Flask
from flask_login import LoginManager

from db.models import Base, User
from db.session import create_engine_and_session
from web.routes import api


def create_app(config: dict[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-me"),
        DATABASE_URL=os.environ.get("DATABASE_URL", "sqlite:///talentscope.db"),
        CREATE_DATABASE=False,
    )
    if config:
        app.config.update(config)

    engine, session_factory = create_engine_and_session(str(app.config["DATABASE_URL"]))
    app.extensions["talentscope_engine"] = engine
    app.extensions["talentscope_session_factory"] = session_factory
    if app.config["CREATE_DATABASE"]:
        Base.metadata.create_all(engine)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        with session_factory() as session:
            return session.get(User, int(user_id))

    app.register_blueprint(api)
    return app
