"""Remotive public API adapter."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from html import unescape
from typing import Any
from urllib.request import urlopen

from core.models import JobPosting

REMOTIVE_JOBS_URL = "https://remotive.com/api/remote-jobs"


def _default_fetch(url: str) -> bytes:
    with urlopen(url, timeout=15) as response:  # noqa: S310 - fixed public API URL
        return response.read()


def _plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))).strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class RemotiveSource:
    """Fetch and normalize remote job postings from Remotive's public JSON API."""

    name = "remotive"

    def __init__(
        self,
        fetcher: Callable[[str], bytes] = _default_fetch,
        url: str = REMOTIVE_JOBS_URL,
    ) -> None:
        self._fetcher = fetcher
        self._url = url

    def fetch(self, since: datetime | None = None) -> list[JobPosting]:
        payload = json.loads(self._fetcher(self._url))
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError("Remotive response must contain a jobs list")

        postings = [self._to_posting(job) for job in jobs if isinstance(job, dict)]
        if since is None:
            return postings
        return [
            job for job in postings if job.posted_at is None or job.posted_at >= since
        ]

    def _to_posting(self, job: dict[str, Any]) -> JobPosting:
        title = self._required_text(job, "title")
        company = self._required_text(job, "company_name")
        link = self._required_text(job, "url")
        tags = job.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        return JobPosting(
            source=self.name,
            title=title,
            company=company,
            location=str(job.get("candidate_required_location") or "Remote"),
            link=link,
            posted_at=_parse_datetime(job.get("publication_date")),
            salary_raw=str(job["salary"]) if job.get("salary") else None,
            skills=tuple(str(tag) for tag in tags),
            description=_plain_text(str(job.get("description") or "")),
        )

    @staticmethod
    def _required_text(job: dict[str, Any], field: str) -> str:
        value = job.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Remotive job is missing required field: {field}")
        return value.strip()
