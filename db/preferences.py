"""Persistence operations for a user's stored preferences."""

from __future__ import annotations

from sqlalchemy.orm import Session

from analysis.skill_merge import merge_skills
from db.models import User, UserPreference


def merge_inferred_skills_into_preferences(
    session: Session, user: User, inferred: list[str]
) -> UserPreference:
    """Get-or-create *user*'s preferences and union *inferred* skills into them.

    Shared by every source that infers skills for a user (GitHub sync,
    LinkedIn import, and future sources) so "merge into preferences" has one
    definition instead of being reimplemented at each call site.
    """
    preference = user.preferences or UserPreference(skills=[])
    if user.preferences is None:
        user.preferences = preference
    preference.skills = merge_skills(preference.skills or [], inferred)
    return preference
