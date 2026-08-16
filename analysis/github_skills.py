"""Infer skills from a user's public GitHub repositories.

Reuses the same vocabulary-based `extract_skills` matcher used for job
postings, so a skill inferred here means the same thing everywhere else in
the product.
"""

from __future__ import annotations

from analysis.skill_extractor import extract_skills
from core.models import GithubRepo


def infer_skills(repos: list[GithubRepo]) -> list[str]:
    """Return the known skills evidenced by *repos*' names, descriptions,
    languages, and topics."""
    blob = " ".join(
        " ".join((repo.name, repo.description, repo.language or "", *repo.topics))
        for repo in repos
    )
    return extract_skills(blob)


def repo_languages(repos: list[GithubRepo]) -> list[str]:
    """Return the distinct languages used across *repos*, alphabetically."""
    return sorted({repo.language for repo in repos if repo.language})
