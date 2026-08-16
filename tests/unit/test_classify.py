from datetime import datetime, timezone

from analysis.classify import classify, is_cs_related
from core.models import JobPosting

NOW = datetime(2026, 8, 16, tzinfo=timezone.utc)


def make_posting(**overrides) -> JobPosting:
    fields = {
        "source": "fixture",
        "title": "Software Development Intern",
        "company": "Example Labs",
        "location": "Bengaluru",
        "link": "https://example.test/jobs/1",
        "description": "",
        "skills": (),
    }
    fields.update(overrides)
    return JobPosting(**fields)


def test_is_cs_related_true_for_known_skill() -> None:
    posting = make_posting(title="Generalist Intern", skills=("python",))
    assert is_cs_related(posting)


def test_is_cs_related_true_for_cs_keyword_in_description() -> None:
    posting = make_posting(
        title="Trainee", description="Assist our backend engineering team."
    )
    assert is_cs_related(posting)


def test_is_cs_related_false_for_unrelated_posting() -> None:
    posting = make_posting(title="Retail Store Associate", description="Handle sales.")
    assert not is_cs_related(posting)


def test_classify_listing_type_internship_vs_job() -> None:
    intern = classify(make_posting(title="Backend Intern"), now=NOW)
    job = classify(make_posting(title="Backend Engineer"), now=NOW)
    assert intern.listing_type == "internship"
    assert job.listing_type == "job"


def test_classify_work_mode_and_pay_type() -> None:
    remote = classify(
        make_posting(location="Remote", description="Paid per hour, flexible."),
        now=NOW,
    )
    onsite = classify(make_posting(location="Bengaluru"), now=NOW)
    hybrid = classify(make_posting(location="Bengaluru (Hybrid)"), now=NOW)

    assert remote.work_mode == "remote"
    assert remote.pay_type == "per_hour"
    assert onsite.work_mode == "onsite"
    assert onsite.pay_type is None
    assert hybrid.work_mode == "hybrid"


def test_classify_duration_and_target_year() -> None:
    posting = make_posting(
        title="Data Intern for Final Year Students",
        description="This is a 6 month internship.",
    )
    result = classify(posting, now=NOW)
    assert result.duration_months == 6
    assert result.target_year == "final"


def test_classify_target_year_defaults_to_any() -> None:
    result = classify(make_posting(), now=NOW)
    assert result.target_year == "any"


def test_classify_expiry_uses_posted_at_and_listing_window() -> None:
    posting = make_posting(title="Backend Intern", posted_at=NOW)
    result = classify(posting, now=NOW)
    assert (result.expires_at - NOW).days == 45


def test_classify_expiry_job_window_is_longer() -> None:
    posting = make_posting(title="Backend Engineer", posted_at=NOW)
    result = classify(posting, now=NOW)
    assert (result.expires_at - NOW).days == 60


def test_classify_expiry_handles_naive_datetimes() -> None:
    posting = make_posting(title="Backend Intern", posted_at=datetime(2026, 8, 16))
    result = classify(posting, now=NOW)
    assert result.expires_at.tzinfo is not None
