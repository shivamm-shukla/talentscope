"""QAEngine selection at the application composition boundary."""

from __future__ import annotations

import os
from collections.abc import Callable

from ai.providers.gemini import GeminiQAEngine, GenerateFn, gemini_generate
from core.interfaces import QAEngine

DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _gemini_generate_fn() -> GenerateFn:
    api_key = _require_env("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    return gemini_generate(api_key, model)


def _create_gemini_engine() -> QAEngine:
    return GeminiQAEngine(generate=_gemini_generate_fn())


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


GENERATE_FN_FACTORIES: dict[str, Callable[[], GenerateFn]] = {
    "gemini": _gemini_generate_fn,
}


def create_generate_fn(name: str = "gemini") -> GenerateFn:
    """Create a raw prompt->text function, for products that need LLM text
    generation without QAEngine's question/job-context shape (e.g. santa
    resume, future santa prep)."""
    try:
        return GENERATE_FN_FACTORIES[name]()
    except KeyError as error:
        supported = ", ".join(sorted(GENERATE_FN_FACTORIES))
        raise ValueError(
            f"Unsupported generate provider {name!r}; choose one of: {supported}"
        ) from error
