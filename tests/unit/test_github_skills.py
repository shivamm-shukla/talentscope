from analysis.github_skills import infer_skills, repo_languages
from core.models import GithubRepo


def repo(**overrides) -> GithubRepo:
    values = {
        "name": "job-matcher",
        "description": "A Flask app for matching internships.",
        "language": "Python",
        "topics": ("sql",),
    }
    values.update(overrides)
    return GithubRepo(**values)


def test_infer_skills_matches_known_vocabulary_across_repo_fields() -> None:
    skills = infer_skills([repo()])

    assert skills == ["python", "sql", "flask"]


def test_infer_skills_returns_empty_for_no_matches() -> None:
    skills = infer_skills(
        [repo(name="notes", description="", language=None, topics=())]
    )

    assert skills == []


def test_repo_languages_deduplicates_and_sorts() -> None:
    languages = repo_languages(
        [repo(language="Python"), repo(language="JavaScript"), repo(language="Python")]
    )

    assert languages == ["JavaScript", "Python"]


def test_repo_languages_ignores_missing_language() -> None:
    assert repo_languages([repo(language=None)]) == []
