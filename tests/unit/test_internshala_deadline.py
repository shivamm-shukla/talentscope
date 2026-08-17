from datetime import UTC, datetime
from pathlib import Path

from sources.internshala import parse_deadline

DETAIL_FIXTURE = Path(__file__).parents[1] / "fixtures" / "internshala" / "detail.html"


def test_parse_deadline_extracts_valid_through_from_fixture() -> None:
    deadline = parse_deadline(DETAIL_FIXTURE.read_text())

    assert deadline == datetime(2026, 9, 16, 23, 59, 59, tzinfo=UTC)


def test_parse_deadline_returns_none_when_json_ld_absent() -> None:
    assert parse_deadline("<html><body>no structured data here</body></html>") is None


def test_parse_deadline_returns_none_when_value_is_malformed() -> None:
    html = '<script type="application/ld+json">{"validThrough": "not-a-date"}</script>'

    assert parse_deadline(html) is None
