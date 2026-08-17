from analysis.outcomes import compute_outcome_stats


def test_empty_input_returns_zeroed_stats() -> None:
    stats = compute_outcome_stats([])

    assert stats.applications_tracked == 0
    assert stats.applied_count == 0
    assert stats.response_rate == 0.0
    assert stats.offer_rate == 0.0
    assert stats.avg_response_hours is None


def test_saved_only_applications_are_tracked_but_excluded_from_rates() -> None:
    stats = compute_outcome_stats(
        [[{"status": "saved", "at": "2026-08-10T00:00:00+00:00"}]]
    )

    assert stats.applications_tracked == 1
    assert stats.applied_count == 0
    assert stats.response_rate == 0.0


def test_applied_with_no_response_counts_toward_applied_not_response() -> None:
    history = [
        {"status": "saved", "at": "2026-08-10T00:00:00+00:00"},
        {"status": "applied", "at": "2026-08-11T00:00:00+00:00"},
    ]

    stats = compute_outcome_stats([history])

    assert stats.applied_count == 1
    assert stats.response_count == 0
    assert stats.response_rate == 0.0


def test_interviewing_after_applied_counts_as_a_response() -> None:
    history = [
        {"status": "saved", "at": "2026-08-10T00:00:00+00:00"},
        {"status": "applied", "at": "2026-08-11T00:00:00+00:00"},
        {"status": "interviewing", "at": "2026-08-13T00:00:00+00:00"},
    ]

    stats = compute_outcome_stats([history])

    assert stats.applied_count == 1
    assert stats.response_count == 1
    assert stats.response_rate == 1.0
    assert stats.avg_response_hours == 48.0


def test_offer_counts_toward_both_response_and_offer_rate() -> None:
    history = [
        {"status": "applied", "at": "2026-08-11T00:00:00+00:00"},
        {"status": "offer", "at": "2026-08-12T00:00:00+00:00"},
    ]

    stats = compute_outcome_stats([history])

    assert stats.response_count == 1
    assert stats.offer_count == 1
    assert stats.offer_rate == 1.0


def test_rates_average_across_multiple_applications() -> None:
    responded = [
        {"status": "applied", "at": "2026-08-11T00:00:00+00:00"},
        {"status": "rejected", "at": "2026-08-12T00:00:00+00:00"},
    ]
    silent = [{"status": "applied", "at": "2026-08-11T00:00:00+00:00"}]

    stats = compute_outcome_stats([responded, silent])

    assert stats.applied_count == 2
    assert stats.response_count == 1
    assert stats.response_rate == 0.5
