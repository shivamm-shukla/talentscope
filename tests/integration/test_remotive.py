from datetime import UTC, datetime
from pathlib import Path

import pytest

from sources.remotive import RemotiveSource

FIXTURE = Path(__file__).parents[1] / "fixtures" / "remotive" / "jobs.json"


def fixture_fetcher(_: str) -> bytes:
    return FIXTURE.read_bytes()


def test_remotive_source_normalizes_saved_response() -> None:
    jobs = RemotiveSource(fetcher=fixture_fetcher).fetch()

    assert len(jobs) == 2
    assert jobs[0].source == "remotive"
    assert jobs[0].skills == ("python", "flask")
    assert jobs[0].description == "Build useful things."
    assert jobs[0].posted_at == datetime(2026, 8, 10, 12, 30, tzinfo=UTC)


def test_remotive_source_filters_by_posted_date() -> None:
    jobs = RemotiveSource(fetcher=fixture_fetcher).fetch(
        since=datetime(2026, 8, 5, tzinfo=UTC)
    )

    assert [job.title for job in jobs] == ["Python Intern"]


def test_remotive_source_rejects_invalid_response_shape() -> None:
    source = RemotiveSource(fetcher=lambda _: b'{"jobs": {}}')

    with pytest.raises(ValueError, match="jobs list"):
        source.fetch()
