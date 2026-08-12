"""Playwright-backed Internshala adapter using embedded job metadata."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from html import unescape

from core.models import JobPosting

INTERNSHALA_INTERNSHIPS_URL = "https://internshala.com/internships/"


def _plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))).strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _location(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(_location(item) for item in value)
    if isinstance(value, dict):
        address = value.get("address")
        if isinstance(address, dict):
            return str(
                address.get("addressLocality")
                or address.get("addressCountry")
                or "Remote"
            )
        return str(value.get("name") or "Remote")
    return str(value or "Remote")


def _organization_name(value: object) -> str:
    if isinstance(value, dict) and isinstance(value.get("name"), str):
        return value["name"]
    return "Unknown company"


def _skills(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(skill.strip() for skill in value.split(",") if skill.strip())
    if isinstance(value, list):
        return tuple(str(skill).strip() for skill in value if str(skill).strip())
    return ()


def _salary(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    amount = value.get("value")
    currency = value.get("currency")
    if isinstance(amount, dict):
        amount = amount.get("value") or amount.get("minValue")
    if amount is None:
        return None
    return f"{currency or ''} {amount}".strip()


def parse_job_postings(document: str) -> list[JobPosting]:
    """Normalize JobPosting JSON-LD blocks from an Internshala listing document."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        document,
        flags=re.IGNORECASE | re.DOTALL,
    )
    postings: list[JobPosting] = []
    for block in blocks:
        try:
            decoded = json.loads(block)
        except json.JSONDecodeError:
            continue
        entries = decoded if isinstance(decoded, list) else [decoded]
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("@type") != "JobPosting":
                continue
            title = entry.get("title")
            url = entry.get("url")
            if not isinstance(title, str) or not isinstance(url, str):
                continue
            postings.append(
                JobPosting(
                    source="internshala",
                    title=title.strip(),
                    company=_organization_name(entry.get("hiringOrganization")),
                    location=_location(entry.get("jobLocation")),
                    link=url.strip(),
                    posted_at=_parse_datetime(entry.get("datePosted")),
                    salary_raw=_salary(entry.get("baseSalary")),
                    skills=_skills(entry.get("skills")),
                    description=_plain_text(str(entry.get("description") or "")),
                )
            )
    return postings


def _fetch_listing_html(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.locator("script[type='application/ld+json']").first.wait_for(
            state="attached"
        )
        html = page.content()
        context.close()
        browser.close()
    return html


class InternshalaSource:
    """Fetch and normalize dynamic Internshala listings through Playwright."""

    name = "internshala"

    def __init__(
        self,
        fetch_html: Callable[[str], str] = _fetch_listing_html,
        url: str = INTERNSHALA_INTERNSHIPS_URL,
    ) -> None:
        self._fetch_html = fetch_html
        self._url = url

    def fetch(self, since: datetime | None = None) -> list[JobPosting]:
        postings = parse_job_postings(self._fetch_html(self._url))
        if since is None:
            return postings
        return [
            job for job in postings if job.posted_at is None or job.posted_at >= since
        ]
