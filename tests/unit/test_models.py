from datetime import datetime

import pytest

from core.models import DateRange, MatchedJob


def test_date_range_rejects_reverse_chronology() -> None:
    with pytest.raises(ValueError, match="end must not be before"):
        DateRange(datetime(2026, 1, 2), datetime(2026, 1, 1))


def test_matched_job_rejects_score_outside_unit_interval() -> None:
    from core.models import JobPosting

    job = JobPosting(
        source="fixture",
        title="Intern",
        company="TalentScope",
        location="Remote",
        link="https://example.test/jobs/1",
    )

    with pytest.raises(ValueError, match="between 0 and 1"):
        MatchedJob(job=job, score=1.1)
