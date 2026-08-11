"""Immutable-ish domain data shared across application modules.

These types deliberately contain no persistence, framework, or provider-specific code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DateRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("DateRange end must not be before its start")


@dataclass(frozen=True, slots=True)
class JobPosting:
    source: str
    title: str
    company: str
    location: str
    link: str
    posted_at: datetime | None = None
    scraped_at: datetime | None = None
    salary_raw: str | None = None
    salary_numeric: int | None = None
    skills: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True, slots=True)
class UserPreferences:
    skills: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    minimum_stipend: int | None = None
    channels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class User:
    id: int | None
    email: str
    name: str = ""
    preferences: UserPreferences = field(default_factory=UserPreferences)


@dataclass(frozen=True, slots=True)
class MatchedJob:
    job: JobPosting
    score: float
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("MatchedJob score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class TrendReport:
    period: DateRange
    total_jobs: int
    skills: dict[str, int] = field(default_factory=dict)
    locations: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    channel: str
    delivered: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class QueryContext:
    user: User | None = None
    jobs: tuple[JobPosting, ...] = ()


@dataclass(frozen=True, slots=True)
class Answer:
    text: str
    sources: tuple[str, ...] = ()
