"""Playwright-backed Internshala adapter, parsed from the listing page's DOM.

Internshala used to embed each posting as JobPosting JSON-LD, but the site no
longer emits that structured data on either the listing or detail pages —
only an unrelated FAQPage/BreadcrumbList/ItemList/SoftwareApplication set of
blocks remains. The listing cards still carry every field we need in plain
HTML, so we scrape those directly instead.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import urljoin

from core.models import JobPosting

INTERNSHALA_INTERNSHIPS_URL = "https://internshala.com/internships/"
INTERNSHALA_BASE_URL = "https://internshala.com"

_CARD_RE = re.compile(
    r'<div class="container-fluid individual_internship[^"]*"[^>]*'
    r'internshipid="(?P<id>\d+)"[^>]*data-href="(?P<href>[^"]+)"[^>]*>'
    r"(?P<body>.*?)"
    r'(?=<div class="container-fluid individual_internship|\Z)',
    re.DOTALL,
)
_TITLE_RE = re.compile(r'class="job-title-href"[^>]*>(.*?)</a>', re.DOTALL)
_COMPANY_RE = re.compile(r'class="company-name">\s*(.*?)\s*</p>', re.DOTALL)
_LOCATION_RE = re.compile(r'class="row-1-item locations">.*?<a>(.*?)</a>', re.DOTALL)
_STIPEND_RE = re.compile(r'class="stipend">([^<]*)</span>')
_SKILL_RE = re.compile(r'class="job_skill">([^<]*)</div>')
_DESCRIPTION_RE = re.compile(
    r'class="about_job">.*?class="text">(.*?)</div>', re.DOTALL
)
_POSTED_RE = re.compile(r'class="status-\w+"><i[^>]*></i><span>([^<]*)</span>')
_RELATIVE_UNIT_RE = re.compile(r"(\d+)\s+(hour|day|week|month)s?\s+ago", re.IGNORECASE)


def _plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))).strip()


def _parse_posted_at(text: str | None, now: datetime) -> datetime | None:
    if not text:
        return None
    normalized = text.strip().lower()
    if normalized in ("today", "few hours ago", "just now"):
        return now
    match = _RELATIVE_UNIT_RE.search(normalized)
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2)
    delta = {
        "hour": timedelta(hours=amount),
        "day": timedelta(days=amount),
        "week": timedelta(weeks=amount),
        "month": timedelta(days=amount * 30),
    }[unit]
    return now - delta


def parse_job_postings(document: str, now: datetime | None = None) -> list[JobPosting]:
    """Normalize job postings from an Internshala listing page's HTML."""
    now = now or datetime.now(timezone.utc)
    postings: list[JobPosting] = []
    for card in _CARD_RE.finditer(document):
        body = card.group("body")
        title = _TITLE_RE.search(body)
        company = _COMPANY_RE.search(body)
        if not title or not company:
            continue
        location = _LOCATION_RE.search(body)
        stipend = _STIPEND_RE.search(body)
        posted = _POSTED_RE.search(body)
        description = _DESCRIPTION_RE.search(body)
        postings.append(
            JobPosting(
                source="internshala",
                title=_plain_text(title.group(1)),
                company=_plain_text(company.group(1)),
                location=_plain_text(location.group(1)) if location else "Remote",
                link=urljoin(INTERNSHALA_BASE_URL, card.group("href")),
                posted_at=_parse_posted_at(posted.group(1) if posted else None, now),
                salary_raw=stipend.group(1).strip() if stipend else None,
                skills=tuple(_SKILL_RE.findall(body)),
                description=_plain_text(description.group(1)) if description else "",
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
        page.locator(".individual_internship").first.wait_for(state="attached")
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
