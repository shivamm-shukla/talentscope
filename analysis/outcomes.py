"""Response-rate and outcome aggregation over tracked applications.

Pure function over plain status-history data (the same shape stored in
``Application.status_history``) rather than ORM objects, so it stays
framework-free and testable like ``analysis/trends.py``.
"""

from __future__ import annotations

from datetime import datetime

from core.models import OutcomeStats

RESPONSE_STATUSES = {"interviewing", "offer", "rejected"}


def _parse_transitions(history: list[dict]) -> list[tuple[str, datetime]]:
    transitions = [
        (entry["status"], datetime.fromisoformat(entry["at"])) for entry in history
    ]
    return sorted(transitions, key=lambda t: t[1])


def compute_outcome_stats(status_histories: list[list[dict]]) -> OutcomeStats:
    """Summarize response/offer behavior across every tracked application.

    "Applied" is the baseline: applications still at "saved" haven't been
    submitted, so they're excluded from response/offer rates (only counted
    in ``applications_tracked``).
    """
    applied_count = response_count = offer_count = 0
    response_hours: list[float] = []

    for history in status_histories:
        transitions = _parse_transitions(history)
        statuses = [status for status, _ in transitions]
        if "applied" not in statuses:
            continue
        applied_count += 1

        applied_at = next(at for status, at in transitions if status == "applied")
        later = [(s, at) for s, at in transitions if at > applied_at]
        response = next((t for t in later if t[0] in RESPONSE_STATUSES), None)
        if response is not None:
            response_count += 1
            response_hours.append((response[1] - applied_at).total_seconds() / 3600)
        if "offer" in statuses:
            offer_count += 1

    return OutcomeStats(
        applications_tracked=len(status_histories),
        applied_count=applied_count,
        response_count=response_count,
        response_rate=response_count / applied_count if applied_count else 0.0,
        offer_count=offer_count,
        offer_rate=offer_count / applied_count if applied_count else 0.0,
        avg_response_hours=(
            sum(response_hours) / len(response_hours) if response_hours else None
        ),
    )
