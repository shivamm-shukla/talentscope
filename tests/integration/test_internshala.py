from datetime import UTC, datetime
from pathlib import Path

import pytest

from sources.internshala import InternshalaSource, parse_job_postings
from sources.registry import create_source

FIXTURE = Path(__file__).parents[1] / "fixtures" / "internshala" / "listings.html"


def fixture_fetcher(_: str) -> str:
    return FIXTURE.read_text()


def test_internshala_source_normalizes_saved_listing() -> None:
    jobs = InternshalaSource(fetch_html=fixture_fetcher).fetch()

    assert len(jobs) == 2
    assert jobs[0].company == "Example Labs"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].salary_raw == "INR 15000"
    assert jobs[0].skills == ("Python", "Flask")
    assert jobs[0].description == "Build web tools."


def test_internshala_source_filters_by_posted_date() -> None:
    jobs = InternshalaSource(fetch_html=fixture_fetcher).fetch(
        since=datetime(2026, 8, 5, tzinfo=UTC)
    )

    assert [job.title for job in jobs] == ["Software Development Intern"]


def test_parser_ignores_invalid_metadata() -> None:
    assert (
        parse_job_postings('<script type="application/ld+json">not-json</script>') == []
    )


def test_source_registry_creates_sources_and_rejects_unknown_names() -> None:
    assert create_source("internshala").name == "internshala"
    assert create_source("remotive").name == "remotive"
    with pytest.raises(ValueError, match="Unsupported job source"):
        create_source("unknown")
