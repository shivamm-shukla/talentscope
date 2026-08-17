"""Compose collected profile data into a structured resume draft.

Every input is optional: a user who has never synced GitHub or imported
LinkedIn (or who signed up purely to use santa resume, not santa scout)
still gets a usable, if sparser, draft — this module never requires data
from another Santa product to produce output.
"""

from __future__ import annotations

MAX_SUMMARY_SKILLS = 8


def _position_bullet(position: dict) -> str:
    title = position.get("title", "").strip()
    company = position.get("company", "").strip()
    description = position.get("description", "").strip()
    role = " at ".join(part for part in (title, company) if part)
    return " — ".join(part for part in (role, description) if part)


def build_resume_draft(
    *,
    skills: list[str] | None = None,
    headline: str = "",
    positions: list[dict] | None = None,
    education: list[str] | None = None,
    certifications: list[str] | None = None,
    languages: list[str] | None = None,
    repo_count: int = 0,
) -> dict[str, dict[str, object]]:
    """Return a ``{section_key: {"heading": str, "bullets": list[str]}}`` draft."""
    skills = skills or []
    positions = positions or []
    education = education or []
    certifications = certifications or []
    languages = languages or []

    summary_bits = []
    if headline:
        summary_bits.append(headline)
    if skills:
        summary_bits.append(f"Skilled in {', '.join(skills[:MAX_SUMMARY_SKILLS])}.")

    projects_bullets = []
    if repo_count:
        languages_note = f" across {', '.join(languages[:5])}" if languages else ""
        projects_bullets.append(
            f"{repo_count} public GitHub repositories{languages_note}"
        )

    experience_bullets = [bullet for p in positions if (bullet := _position_bullet(p))]

    sections: dict[str, dict[str, object]] = {
        "summary": {
            "heading": "Summary",
            "bullets": summary_bits,
        },
        "skills": {"heading": "Skills", "bullets": skills},
        "projects": {"heading": "Projects", "bullets": projects_bullets},
        "experience": {"heading": "Experience", "bullets": experience_bullets},
        "education": {"heading": "Education", "bullets": list(education)},
    }
    if certifications:
        sections["certifications"] = {
            "heading": "Certifications",
            "bullets": list(certifications),
        }
    return sections
