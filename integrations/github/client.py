"""GitHub public REST API adapter — fetches a user's non-fork repositories."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core.models import GithubRepo

GITHUB_API_URL = "https://api.github.com"

Fetcher = Callable[[str, dict[str, str]], bytes]


class GitHubProfileNotFound(Exception):
    """Raised when the requested GitHub username has no public profile."""


def _default_fetch(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed GitHub host
        return response.read()


def fetch_public_repos(
    username: str,
    fetcher: Fetcher = _default_fetch,
    token: str | None = None,
    api_url: str = GITHUB_API_URL,
) -> list[GithubRepo]:
    """Return *username*'s public, non-fork repositories."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SantaScoutBot/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"{api_url}/users/{username}/repos?per_page=100&type=owner"
    try:
        raw = fetcher(url, headers)
    except HTTPError as error:
        if error.code == 404:
            raise GitHubProfileNotFound(str(error)) from error
        raise

    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("GitHub repos response must be a list")

    repos = [_to_repo(entry) for entry in payload if isinstance(entry, dict)]
    return [repo for repo in repos if not repo.fork]


def _to_repo(entry: dict[str, Any]) -> GithubRepo:
    topics = entry.get("topics", [])
    return GithubRepo(
        name=str(entry.get("name") or ""),
        description=str(entry.get("description") or ""),
        language=(
            entry.get("language") if isinstance(entry.get("language"), str) else None
        ),
        topics=(
            tuple(str(topic) for topic in topics) if isinstance(topics, list) else ()
        ),
        fork=bool(entry.get("fork", False)),
    )
