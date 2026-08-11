"""Pure, deterministic TalentScope analysis functions."""

from analysis.salary import normalize_monthly_stipend
from analysis.skill_extractor import extract_skills
from analysis.trends import compute_trends

__all__ = ["compute_trends", "extract_skills", "normalize_monthly_stipend"]
