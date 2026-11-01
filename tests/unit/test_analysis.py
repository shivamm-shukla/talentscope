from datetime import UTC, datetime

from analysis.salary import normalize_monthly_stipend
from analysis.skill_extractor import extract_skills
from analysis.trends import compute_trends, stipend_distribution
from core.models import DateRange, JobPosting


def test_skill_extraction_is_case_insensitive_and_word_bounded() -> None:
    assert extract_skills("Python, React and SQL; not javascripting") == [
        "python",
        "sql",
        "react",
    ]


def test_stipend_normalization_handles_common_formats() -> None:
    assert normalize_monthly_stipend("₹15,000/month") == 15_000
    assert normalize_monthly_stipend("INR 1.2 lakh per annum") == 10_000
    assert normalize_monthly_stipend("Unpaid") is None


def test_trends_count_only_postings_inside_period() -> None:
    period = DateRange(
        datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 8, 31, tzinfo=UTC)
    )
    jobs = [
        JobPosting(
            "x",
            "A",
            "Co",
            "Bengaluru",
            "https://a",
            datetime(2026, 8, 2, tzinfo=UTC),
            skills=("Python", "SQL"),
        ),
        JobPosting(
            "x",
            "B",
            "Co",
            "Remote",
            "https://b",
            datetime(2026, 8, 3, tzinfo=UTC),
            skills=("Python",),
        ),
        JobPosting(
            "x",
            "C",
            "Co",
            "Remote",
            "https://c",
            datetime(2026, 7, 31, tzinfo=UTC),
            skills=("React",),
        ),
    ]

    report = compute_trends(jobs, period)

    assert report.total_jobs == 2
    assert report.skills == {"python": 2, "sql": 1}
    assert report.locations == {"Bengaluru": 1, "Remote": 1}


def test_stipend_distribution_buckets_by_lower_bound_inclusive() -> None:
    assert stipend_distribution([5_000, 10_000, 19_999, 25_000, 50_000, 80_000]) == {
        "<10k": 1,
        "10-20k": 2,
        "20-30k": 1,
        "30-50k": 0,
        ">50k": 2,
    }
