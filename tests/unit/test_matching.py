from core.models import JobPosting, UserPreferences
from matching.matcher import match_jobs


def job(**overrides) -> JobPosting:
    values = {
        "source": "fixture",
        "title": "Python Intern",
        "company": "Example Co",
        "location": "Bengaluru",
        "link": "https://example.test/jobs/1",
        "skills": ("Python", "Flask"),
        "salary_numeric": 15_000,
    }
    values.update(overrides)
    return JobPosting(**values)


def test_matcher_scores_and_explains_matching_job() -> None:
    preferences = UserPreferences(
        skills=("python", "sql"), locations=("bengaluru",), minimum_stipend=12_000
    )

    matches = match_jobs(preferences, [job()])

    assert len(matches) == 1
    assert matches[0].score == 0.55
    assert matches[0].reasons == (
        "skills: python",
        "location: Bengaluru",
        "stipend meets minimum",
    )


def test_matcher_excludes_jobs_outside_required_location_or_stipend() -> None:
    preferences = UserPreferences(locations=("bengaluru",), minimum_stipend=12_000)

    assert (
        match_jobs(preferences, [job(location="Remote"), job(salary_numeric=8_000)])
        == []
    )


def test_matcher_excludes_jobs_with_no_skill_overlap_from_skills_only_preference() -> (
    None
):
    preferences = UserPreferences(skills=("python",))

    assert match_jobs(preferences, [job(skills=("Java", "Spring"))]) == []
    assert len(match_jobs(preferences, [job(skills=("Python",))])) == 1


def test_matcher_ranks_more_relevant_jobs_first() -> None:
    preferences = UserPreferences(skills=("python", "sql"))
    less_relevant = job(title="A job", skills=("Python",))
    more_relevant = job(title="Z job", skills=("Python", "SQL"))

    assert [
        match.job.title
        for match in match_jobs(preferences, [less_relevant, more_relevant])
    ] == ["Z job", "A job"]


def test_matcher_includes_partial_skill_matches_ranked_by_confidence() -> None:
    """A single-skill preference should surface every job that needs that skill,
    not just jobs whose skill list matches exactly — but a job that also
    requires skills outside the user's preference should rank lower than one
    that doesn't, since the user is a closer fit for the smaller ask."""
    preferences = UserPreferences(skills=("python",))
    close_fit = job(title="Python + SQL role", skills=("Python", "SQL"))
    broader_ask = job(
        title="Python + SQL + Java role", skills=("Python", "SQL", "Java")
    )

    matches = match_jobs(preferences, [broader_ask, close_fit])

    assert [match.job.title for match in matches] == [
        "Python + SQL role",
        "Python + SQL + Java role",
    ]
    assert matches[0].score > matches[1].score
