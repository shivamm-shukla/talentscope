"""Deterministic posting-quality scoring: no ML, just a repost signal.

A "stale, listed past its estimated window" signal was considered for v1
but doesn't hold up against how this pipeline actually behaves:
`db/jobs.py::prune_expired_jobs` already deletes any job past its
`expires_at` estimate in the same pipeline run, before this scoring even
executes — so a job can never be observed past that window, and a
staleness check against it would be dead code. Repost detection has no
such issue: `upsert_job` refreshes `posted_at` whenever a posting
reappears under the same identity, which is exactly the "kept artificially
alive by relisting" pattern worth flagging.
"""

from __future__ import annotations

from datetime import datetime, timedelta

DEFAULT_REPOST_GAP = timedelta(hours=6)
FLAG_PENALTY = 40


def _has_repost_gap(observed_at: list[datetime], gap_threshold: timedelta) -> bool:
    """A gap larger than *gap_threshold* between consecutive sightings means
    the posting dropped off at least one scrape cycle before reappearing."""
    timestamps = sorted(observed_at)
    return any(
        later - earlier > gap_threshold
        for earlier, later in zip(timestamps, timestamps[1:])
    )


def score_job(
    *,
    observed_at: list[datetime],
    repost_gap: timedelta = DEFAULT_REPOST_GAP,
) -> tuple[int, list[str]]:
    """Return ``(quality_score, flags)`` for a job, 100 = no signal found."""
    flags = ["reposted"] if _has_repost_gap(observed_at, repost_gap) else []
    score = max(0, 100 - FLAG_PENALTY * len(flags))
    return score, flags
