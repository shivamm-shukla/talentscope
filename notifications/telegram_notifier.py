"""Telegram Bot API notifier."""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.request import Request, urlopen

from core.models import DeliveryResult, MatchedJob, User

TELEGRAM_API_URL = "https://api.telegram.org"
MAX_DIGEST_ITEMS = 5

Poster = Callable[[str, bytes], bytes]


def _default_poster(url: str, payload: bytes) -> bytes:
    request = Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed Telegram host
        return response.read()


def _format_text(matches: list[MatchedJob], site_url: str | None) -> str:
    ordered = sorted(matches, key=lambda match: -match.score)
    shown = ordered[:MAX_DIGEST_ITEMS]
    remaining = len(ordered) - len(shown)
    lines = [
        f"- {match.job.title} at {match.job.company} ({match.job.location}): "
        f"{match.job.link}"
        for match in shown
    ]
    text = "New job matches:\n\n" + "\n".join(lines)
    if remaining > 0:
        text += f"\n\n+{remaining} more match{'es' if remaining != 1 else ''}"
        if site_url:
            text += f" — see them all at {site_url}"
    return text


class TelegramNotifier:
    """Sends match digests through a Telegram bot's sendMessage endpoint."""

    channel = "telegram"

    def __init__(
        self,
        bot_token: str,
        poster: Poster = _default_poster,
        api_url: str = TELEGRAM_API_URL,
        site_url: str | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._poster = poster
        self._api_url = api_url
        self._site_url = site_url

    def send(self, user: User, matches: list[MatchedJob]) -> DeliveryResult:
        if not matches:
            return DeliveryResult(
                channel=self.channel, delivered=False, detail="no matches to send"
            )
        if not user.telegram_chat_id:
            return DeliveryResult(
                channel=self.channel,
                delivered=False,
                detail="user has no telegram chat id",
            )

        payload = json.dumps(
            {
                "chat_id": user.telegram_chat_id,
                "text": _format_text(matches, self._site_url),
            }
        ).encode("utf-8")
        url = f"{self._api_url}/bot{self._bot_token}/sendMessage"

        try:
            response = json.loads(self._poster(url, payload))
        except (OSError, ValueError) as error:
            return DeliveryResult(
                channel=self.channel, delivered=False, detail=str(error)
            )
        if not response.get("ok"):
            detail = str(response.get("description", "telegram error"))
            return DeliveryResult(channel=self.channel, delivered=False, detail=detail)
        return DeliveryResult(
            channel=self.channel,
            delivered=True,
            detail=f"sent to chat {user.telegram_chat_id}",
        )
