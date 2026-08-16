"""Infer skills from a user's LinkedIn data export.

Reuses the same vocabulary-based `extract_skills` matcher used for job
postings and GitHub repos, so a skill inferred here means the same thing
everywhere else in the product.
"""

from __future__ import annotations

from analysis.skill_extractor import extract_skills
from analysis.skill_merge import merge_skills
from core.models import LinkedinExport


def infer_skills(export: LinkedinExport) -> list[str]:
    """Return the known skills evidenced by *export*'s positions, education,
    and certifications, unioned with LinkedIn's own literal skill names."""
    blob = " ".join(
        (
            export.headline,
            *(
                " ".join((position.title, position.company, position.description))
                for position in export.positions
            ),
            *export.education,
            *export.certifications,
        )
    )
    return merge_skills(extract_skills(blob), list(export.skills))
