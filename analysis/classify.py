"""Deterministic CS-relevance and taxonomy classification for job postings.

Scope decision: this product only serves CS/BCA/computer-related-course
students, so every posting is screened for CS relevance before it is stored,
and classified along the axes students actually filter by.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from analysis.skill_extractor import KNOWN_SKILLS
from core.models import JobPosting

CS_KEYWORDS = (
    "software",
    "developer",
    "development",
    "programming",
    "programmer",
    "computer science",
    "computer application",
    "engineer",
    "engineering intern",
    "backend",
    "back-end",
    "frontend",
    "front-end",
    "full stack",
    "fullstack",
    "web development",
    "app development",
    "mobile development",
    "android",
    "ios developer",
    "data science",
    "data analyst",
    "data engineer",
    "machine learning",
    "artificial intelligence",
    "deep learning",
    "devops",
    "cloud engineer",
    "cyber security",
    "cybersecurity",
    "network security",
    "qa engineer",
    "quality assurance",
    "sde",
    "information technology",
    "database administrator",
    "systems administrator",
)

_INTERNSHIP_RE = re.compile(r"\bintern(ship)?\b", re.IGNORECASE)
_REMOTE_RE = re.compile(r"\b(remote|work[\s-]?from[\s-]?home|wfh)\b", re.IGNORECASE)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)
_PER_HOUR_RE = re.compile(r"\b(per\s?hour|/\s?hr|hourly)\b", re.IGNORECASE)
_PER_TASK_RE = re.compile(r"\b(per\s?task|project[\s-]?based|\bgig\b)\b", re.IGNORECASE)
_DURATION_RE = re.compile(r"(\d+)(?:\s*-\s*\d+)?\s*months?\b", re.IGNORECASE)
_YEAR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("1st", re.compile(r"\b(1st|first)[\s-]?year\b", re.IGNORECASE)),
    ("2nd", re.compile(r"\b(2nd|second)[\s-]?year\b", re.IGNORECASE)),
    ("3rd", re.compile(r"\b(3rd|third)[\s-]?year\b", re.IGNORECASE)),
    ("final", re.compile(r"\b(final|4th|fourth|last)[\s-]?year\b", re.IGNORECASE)),
)

INTERNSHIP_RETENTION_DAYS = 45
JOB_RETENTION_DAYS = 60


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def is_cs_related(posting: JobPosting) -> bool:
    """CS/BCA scope filter: a known CS skill or a CS keyword anywhere in the text."""
    if any(skill.casefold() in KNOWN_SKILLS for skill in posting.skills):
        return True
    haystack = f"{posting.title} {posting.description}".casefold()
    return any(keyword in haystack for keyword in CS_KEYWORDS)


def classify_listing_type(posting: JobPosting) -> str:
    return "internship" if _INTERNSHIP_RE.search(posting.title) else "job"


def classify_work_mode(posting: JobPosting) -> str:
    haystack = f"{posting.location} {posting.description}"
    if _HYBRID_RE.search(haystack):
        return "hybrid"
    if _REMOTE_RE.search(haystack):
        return "remote"
    return "onsite"


def classify_pay_type(posting: JobPosting, work_mode: str) -> str | None:
    """Only meaningful for remote work, per the agreed taxonomy."""
    if work_mode != "remote":
        return None
    if _PER_HOUR_RE.search(posting.description):
        return "per_hour"
    if _PER_TASK_RE.search(posting.description):
        return "per_task"
    return "fixed_stipend"


def estimate_duration_months(posting: JobPosting) -> int | None:
    match = _DURATION_RE.search(posting.description)
    return int(match.group(1)) if match else None


def estimate_target_year(posting: JobPosting) -> str:
    haystack = f"{posting.title} {posting.description}"
    for year, pattern in _YEAR_PATTERNS:
        if pattern.search(haystack):
            return year
    return "any"


def estimate_expiry(posting: JobPosting, listing_type: str, now: datetime) -> datetime:
    """No source gives an explicit deadline, so fall back to a retention window
    anchored on the posting's own date — internships churn faster than jobs."""
    window = (
        INTERNSHIP_RETENTION_DAYS
        if listing_type == "internship"
        else JOB_RETENTION_DAYS
    )
    anchor = _as_utc(posting.posted_at) or _as_utc(posting.scraped_at) or now
    return anchor + timedelta(days=window)


@dataclass(frozen=True, slots=True)
class Classification:
    is_cs_related: bool
    listing_type: str
    work_mode: str
    pay_type: str | None
    duration_months: int | None
    target_year: str
    expires_at: datetime


def classify(posting: JobPosting, now: datetime | None = None) -> Classification:
    now = now or datetime.now(timezone.utc)
    listing_type = classify_listing_type(posting)
    work_mode = classify_work_mode(posting)
    return Classification(
        is_cs_related=is_cs_related(posting),
        listing_type=listing_type,
        work_mode=work_mode,
        pay_type=classify_pay_type(posting, work_mode),
        duration_months=estimate_duration_months(posting),
        target_year=estimate_target_year(posting),
        expires_at=estimate_expiry(posting, listing_type, now),
    )
