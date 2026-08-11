"""Database configuration and persistence models for TalentScope."""

from db.models import Base
from db.session import create_engine_and_session

__all__ = ["Base", "create_engine_and_session"]
