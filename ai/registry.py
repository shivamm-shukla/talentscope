"""QAEngine selection at the application composition boundary."""

from __future__ import annotations

import os
from collections.abc import Callable

from ai.providers.gemini import GeminiQAEngine, gemini_generate
from core.interfaces import QAEngine

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _create_gemini_engine() -> QAEngine:
    api_key = _require_env("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    return GeminiQAEngine(generate=gemini_generate(api_key, model))


QA_ENGINE_FACTORIES: dict[str, Callable[[], QAEngine]] = {
    "gemini": _create_gemini_engine,
}


def create_qa_engine(name: str = "gemini") -> QAEngine:
    """Create a configured QA engine by its stable configuration name."""
    try:
        return QA_ENGINE_FACTORIES[name]()
    except KeyError as error:
        supported = ", ".join(sorted(QA_ENGINE_FACTORIES))
        raise ValueError(
            f"Unsupported QA engine {name!r}; choose one of: {supported}"
        ) from error
