"""Trend computation over normalized job postings."""

from collections import Counter

from core.models import DateRange, JobPosting, TrendReport


def compute_trends(jobs: list[JobPosting], period: DateRange) -> TrendReport:
    """Count job, skill, and location demand within an inclusive date range."""
    in_period = [
        job
        for job in jobs
        if job.posted_at is not None and period.start <= job.posted_at <= period.end
    ]
    skills = Counter(skill.casefold() for job in in_period for skill in job.skills)
    locations = Counter(job.location for job in in_period)
    return TrendReport(
        period=period,
        total_jobs=len(in_period),
        skills=dict(skills.most_common()),
        locations=dict(locations.most_common()),
    )


STIPEND_BUCKETS: tuple[tuple[str, int, int | None], ...] = (
    ("<10k", 0, 10_000),
    ("10-20k", 10_000, 20_000),
    ("20-30k", 20_000, 30_000),
    ("30-50k", 30_000, 50_000),
    (">50k", 50_000, None),
)


def stipend_distribution(stipends: list[int]) -> dict[str, int]:
    """Bucket monthly stipends (rupees) into fixed ranges, lower bound inclusive."""
    counts = {label: 0 for label, _, _ in STIPEND_BUCKETS}
    for stipend in stipends:
        for label, low, high in STIPEND_BUCKETS:
            if stipend >= low and (high is None or stipend < high):
                counts[label] += 1
                break
    return counts
