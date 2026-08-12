"""Notifier selection at the application composition boundary."""

from __future__ import annotations

import os
from collections.abc import Callable

from core.interfaces import Notifier
from notifications.email_notifier import EmailNotifier, smtp_factory
from notifications.telegram_notifier import TelegramNotifier


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _create_email_notifier() -> Notifier:
    return EmailNotifier(
        sender_address=_require_env("SMTP_SENDER"),
        smtp_factory=smtp_factory(
            host=_require_env("SMTP_HOST"),
            port=int(os.environ.get("SMTP_PORT", "587")),
            username=_require_env("SMTP_USERNAME"),
            password=_require_env("SMTP_PASSWORD"),
        ),
    )


def _create_telegram_notifier() -> Notifier:
    return TelegramNotifier(bot_token=_require_env("TELEGRAM_BOT_TOKEN"))


NOTIFIER_FACTORIES: dict[str, Callable[[], Notifier]] = {
    "email": _create_email_notifier,
    "telegram": _create_telegram_notifier,
}


def create_notifier(name: str) -> Notifier:
    """Create a configured notifier by its stable configuration name."""
    try:
        return NOTIFIER_FACTORIES[name]()
    except KeyError as error:
        supported = ", ".join(sorted(NOTIFIER_FACTORIES))
        raise ValueError(
            f"Unsupported notification channel {name!r}; choose one of: {supported}"
        ) from error
