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
