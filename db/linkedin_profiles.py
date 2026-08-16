"""Persistence operations for imported LinkedIn profile snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.models import LinkedinExport
from db.models import LinkedinProfile, User


def upsert_linkedin_profile(
    session: Session,
    user: User,
    export: LinkedinExport,
    inferred_skills: list[str],
) -> LinkedinProfile:
    """Insert or refresh *user*'s imported LinkedIn snapshot."""
    stored = user.linkedin_profile
    if stored is None:
        stored = LinkedinProfile(user=user)
        session.add(stored)
    stored.headline = export.headline
    stored.positions = [
        {"title": p.title, "company": p.company, "description": p.description}
        for p in export.positions
    ]
    stored.education = list(export.education)
    stored.certifications = list(export.certifications)
    stored.inferred_skills = inferred_skills
    stored.synced_at = datetime.now(UTC)
    return stored
