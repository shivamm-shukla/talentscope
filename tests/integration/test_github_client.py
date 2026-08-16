import json
from pathlib import Path

import pytest

from integrations.github.client import GitHubProfileNotFound, fetch_public_repos

FIXTURE = Path(__file__).parents[1] / "fixtures" / "github" / "repos.json"


def fixture_fetcher(_url: str, _headers: dict[str, str]) -> bytes:
    return FIXTURE.read_bytes()


def test_fetch_public_repos_normalizes_and_drops_forks() -> None:
    repos = fetch_public_repos("octocat", fetcher=fixture_fetcher)

    assert [repo.name for repo in repos] == ["job-matcher", "portfolio-site"]
    assert repos[0].language == "Python"
    assert repos[0].topics == ("python", "flask", "sql")


def test_fetch_public_repos_sends_token_when_provided() -> None:
    captured = {}

    def fetcher(url: str, headers: dict[str, str]) -> bytes:
        captured["url"] = url
        captured["headers"] = headers
        return FIXTURE.read_bytes()

    fetch_public_repos("octocat", fetcher=fetcher, token="secret")

    assert captured["headers"]["Authorization"] == "token secret"
    assert "octocat" in captured["url"]


def test_fetch_public_repos_rejects_invalid_response_shape() -> None:
    with pytest.raises(ValueError, match="must be a list"):
        fetch_public_repos("octocat", fetcher=lambda *_: json.dumps({}).encode())


def test_fetch_public_repos_raises_profile_not_found() -> None:
    from urllib.error import HTTPError

    def not_found_fetcher(_url: str, _headers: dict[str, str]) -> bytes:
        raise HTTPError("url", 404, "Not Found", None, None)

    with pytest.raises(GitHubProfileNotFound):
        fetch_public_repos("does-not-exist", fetcher=not_found_fetcher)
