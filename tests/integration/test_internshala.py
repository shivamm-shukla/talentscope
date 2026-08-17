from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sources.internshala import InternshalaSource, parse_job_postings
from sources.registry import create_source
from sources.remotive import RemotiveSource

FIXTURE = Path(__file__).parents[1] / "fixtures" / "internshala" / "listings.html"
DETAIL_FIXTURE = Path(__file__).parents[1] / "fixtures" / "internshala" / "detail.html"


def fixture_fetcher(_: str) -> str:
    return FIXTURE.read_text()


def detail_fixture_fetcher(_: str) -> str:
    return DETAIL_FIXTURE.read_text()


def source(**overrides) -> InternshalaSource:
    values = {
        "fetch_html": fixture_fetcher,
        "fetch_detail_html": detail_fixture_fetcher,
    }
    values.update(overrides)
    return InternshalaSource(**values)


def test_internshala_source_normalizes_saved_listing() -> None:
    jobs = source().fetch()

    assert len(jobs) == 2
    assert jobs[0].title == "Software Development Intern"
    assert jobs[0].company == "Example Labs"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].salary_raw == "₹ 15,000 /month"
    assert jobs[0].skills == ("Python", "Flask")
    assert jobs[0].description == "Build web tools."


def test_internshala_source_filters_by_posted_date() -> None:
    since = datetime.now(UTC) - timedelta(days=10)
    jobs = source().fetch(since=since)

    assert [job.title for job in jobs] == ["Software Development Intern"]


def test_internshala_source_populates_deadline_from_detail_page() -> None:
    jobs = source().fetch()

    assert jobs[0].deadline_at == datetime(2026, 9, 16, 23, 59, 59, tzinfo=UTC)
    assert jobs[1].deadline_at == datetime(2026, 9, 16, 23, 59, 59, tzinfo=UTC)


def test_internshala_source_isolates_detail_page_failures() -> None:
    def flaky_detail_fetcher(url: str) -> str:
        if "456" in url:
            raise TimeoutError("detail page timed out")
        return DETAIL_FIXTURE.read_text()

    jobs = source(fetch_detail_html=flaky_detail_fetcher).fetch()

    assert len(jobs) == 2
    by_title = {job.title: job for job in jobs}
    assert by_title["Software Development Intern"].deadline_at is not None
    assert by_title["Data Intern"].deadline_at is None


def test_parser_ignores_cards_missing_required_fields() -> None:
    assert parse_job_postings("<div>no internship cards here</div>") == []


def test_source_registry_creates_sources_and_rejects_unknown_names() -> None:
    internshala = create_source("internshala")
    remotive = create_source("remotive")

    assert isinstance(internshala, InternshalaSource)
    assert internshala.name == "internshala"
    assert isinstance(remotive, RemotiveSource)
    assert remotive.name == "remotive"
    with pytest.raises(ValueError, match="Unsupported job source"):
        create_source("unknown")
