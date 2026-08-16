from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sources.internshala import InternshalaSource, parse_job_postings
from sources.registry import create_source
from sources.remotive import RemotiveSource

FIXTURE = Path(__file__).parents[1] / "fixtures" / "internshala" / "listings.html"


def fixture_fetcher(_: str) -> str:
    return FIXTURE.read_text()


def test_internshala_source_normalizes_saved_listing() -> None:
    jobs = InternshalaSource(fetch_html=fixture_fetcher).fetch()

    assert len(jobs) == 2
    assert jobs[0].title == "Software Development Intern"
    assert jobs[0].company == "Example Labs"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].salary_raw == "₹ 15,000 /month"
    assert jobs[0].skills == ("Python", "Flask")
    assert jobs[0].description == "Build web tools."


def test_internshala_source_filters_by_posted_date() -> None:
    since = datetime.now(UTC) - timedelta(days=10)
    jobs = InternshalaSource(fetch_html=fixture_fetcher).fetch(since=since)

    assert [job.title for job in jobs] == ["Software Development Intern"]


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
