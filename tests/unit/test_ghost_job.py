from datetime import datetime, timedelta, timezone

from analysis.ghost_job import score_job

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)


def test_score_job_with_no_gap_is_clean() -> None:
    score, flags = score_job(observed_at=[NOW - timedelta(hours=2), NOW])

    assert score == 100
    assert flags == []


def test_score_job_flags_repost_gap() -> None:
    score, flags = score_job(
        observed_at=[NOW - timedelta(days=1), NOW],
        repost_gap=timedelta(hours=6),
    )

    assert flags == ["reposted"]
    assert score == 60


def test_score_job_with_zero_or_one_observations_is_never_flagged() -> None:
    assert score_job(observed_at=[]) == (100, [])
    assert score_job(observed_at=[NOW]) == (100, [])
