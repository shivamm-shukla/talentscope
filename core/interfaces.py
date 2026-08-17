"""Structural contracts between Santa modules."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from core.models import (
    Answer,
    DateRange,
    DeadlineReminder,
    DeliveryResult,
    JobPosting,
    MatchedJob,
    QueryContext,
    TrendReport,
    User,
    UserPreferences,
)


class JobSource(Protocol):
    name: str

    def fetch(self, since: datetime | None = None) -> list[JobPosting]: ...


class SkillExtractor(Protocol):
    def extract(self, text: str) -> list[str]: ...


class TrendAnalyzer(Protocol):
    def compute(self, jobs: list[JobPosting], period: DateRange) -> TrendReport: ...


class Matcher(Protocol):
    def match(
        self, prefs: UserPreferences, jobs: list[JobPosting]
    ) -> list[MatchedJob]: ...


class Notifier(Protocol):
    channel: str

    def send(self, user: User, matches: list[MatchedJob]) -> DeliveryResult: ...
    def remind(
        self, user: User, reminders: list[DeadlineReminder]
    ) -> DeliveryResult: ...


class QAEngine(Protocol):
    def answer(self, question: str, context: QueryContext) -> Answer: ...
