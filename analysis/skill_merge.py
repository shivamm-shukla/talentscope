"""Merge newly inferred skills into an existing skill list."""

from __future__ import annotations


def merge_skills(existing: list[str], inferred: list[str]) -> list[str]:
    """Union *inferred* into *existing*, case-insensitively, keeping the
    existing entries' casing and only appending genuinely new skills."""
    seen = {skill.casefold() for skill in existing}
    merged = list(existing)
    for skill in inferred:
        if skill.casefold() not in seen:
            merged.append(skill)
            seen.add(skill.casefold())
    return merged
