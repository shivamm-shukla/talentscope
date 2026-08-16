"""Sync users' GitHub activity and refresh their inferred skill preferences."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from analysis.github_skills import infer_skills, repo_languages
from core.logging import configure_json_logging
from core.models import GithubRepo
from db.github_profiles import upsert_github_profile
from db.models import User, UserPreference
from db.session import create_engine_and_session
from integrations.github.client import fetch_public_repos

FetchRepos = Callable[[str], list[GithubRepo]]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GithubSyncResult:
    users_synced: int
    skills_added: int
    failed: int


def _merge_skills(existing: list[str], inferred: list[str]) -> list[str]:
    """Union *inferred* into *existing*, case-insensitively, keeping the
    existing entries' casing and only appending genuinely new skills."""
    seen = {skill.casefold() for skill in existing}
    merged = list(existing)
    for skill in inferred:
        if skill.casefold() not in seen:
            merged.append(skill)
            seen.add(skill.casefold())
    return merged


def run(
    session: Session,
    token: str | None = None,
    fetch: FetchRepos | None = None,
) -> GithubSyncResult:
    """Fetch and re-infer skills for every user with a linked GitHub username.

    Each user is synced independently: one user's GitHub failure (404,
    rate limit, network error) is logged and skipped rather than blocking
    the rest, matching the per-source isolation used elsewhere in the
    pipeline.
    """
    fetch = fetch or (lambda username: fetch_public_repos(username, token=token))
    users = list(
        session.scalars(
            select(User)
            .where(User.github_username.is_not(None))
            .options(selectinload(User.preferences), selectinload(User.github_profile))
        ).all()
    )
    users_synced = skills_added = failed = 0
    for user in users:
        try:
            repos = fetch(user.github_username)
        except Exception:
            logger.exception("github sync failed for user %s; skipping", user.id)
            failed += 1
            continue

        inferred = infer_skills(repos)
        preference = user.preferences or UserPreference(skills=[])
        if user.preferences is None:
            user.preferences = preference
        existing_skills = preference.skills or []
        before = len(existing_skills)
        preference.skills = _merge_skills(existing_skills, inferred)
        skills_added += len(preference.skills) - before

        upsert_github_profile(
            session,
            user,
            repo_count=len(repos),
            languages=repo_languages(repos),
            inferred_skills=inferred,
        )
        users_synced += 1

    session.commit()
    return GithubSyncResult(
        users_synced=users_synced, skills_added=skills_added, failed=failed
    )


def main() -> None:
    configure_json_logging()
    parser = argparse.ArgumentParser(
        description="Sync users' GitHub activity into their skill preferences."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("provide --database-url or set DATABASE_URL")
    engine, session_factory = create_engine_and_session(arguments.database_url)
    try:
        with session_factory() as session:
            result = run(session, token=os.environ.get("GITHUB_TOKEN"))
        logger.info(
            "github sync completed",
            extra={
                "users_synced": result.users_synced,
                "skills_added": result.skills_added,
                "failed": result.failed,
            },
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
