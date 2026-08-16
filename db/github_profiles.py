"""Persistence operations for synced GitHub profile snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from db.models import GithubProfile, User


def upsert_github_profile(
    session: Session,
    user: User,
    repo_count: int,
    languages: list[str],
    inferred_skills: list[str],
) -> GithubProfile:
    """Insert or refresh *user*'s synced GitHub snapshot."""
    stored = user.github_profile
    if stored is None:
        stored = GithubProfile(user=user)
        session.add(stored)
    stored.repo_count = repo_count
    stored.languages = languages
    stored.inferred_skills = inferred_skills
    stored.synced_at = datetime.now(UTC)
    return stored
