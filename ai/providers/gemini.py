"""Gemini-backed QAEngine implementation."""

from __future__ import annotations

from collections.abc import Callable

from core.models import Answer, JobPosting, QueryContext

GenerateFn = Callable[[str], str]

# Comfortably under gunicorn's worker timeout, so a slow or stuck call fails
# as a normal error (502 to the user) instead of the worker being killed.
GEMINI_TIMEOUT_MS = 25_000


def gemini_generate(api_key: str, model: str) -> GenerateFn:
    """Build a generate function that calls the real Gemini API on demand.

    Uses the `google-genai` SDK (plain HTTPS). The old `google-generativeai`
    SDK is end-of-life and talked gRPC, which hung on Render until gunicorn
    killed the worker — every AI feature failed with no response.
    """
    client = None

    def generate(prompt: str) -> str:
        nonlocal client
        if client is None:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
            )
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text or ""

    return generate


def _build_prompt(question: str, context: QueryContext) -> str:
    lines = [
        "You are santa scout's internship Q&A assistant.",
        "Answer the student's question using only the job listings below.",
        "",
        f"Question: {question}",
        "",
        "Job listings:",
    ]
    if context.jobs:
        lines.extend(
            f"- {job.title} at {job.company} ({job.location}): {job.link}"
            for job in context.jobs
        )
    else:
        lines.append("(no jobs available)")
    return "\n".join(lines)


def _referenced_jobs(text: str, jobs: tuple[JobPosting, ...]) -> tuple[JobPosting, ...]:
    """Return only the jobs Gemini's answer actually mentions by title or
    company, instead of every job that was in the prompt — the prompt lists
    everything for Gemini to consider, but most questions are only about a
    handful of them."""
    normalized = text.casefold()
    return tuple(
        job
        for job in jobs
        if job.title.casefold() in normalized or job.company.casefold() in normalized
    )


class GeminiQAEngine:
    """Answers questions about persisted job data using Gemini."""

    def __init__(self, generate: GenerateFn) -> None:
        self._generate = generate

    def answer(self, question: str, context: QueryContext) -> Answer:
        text = self._generate(_build_prompt(question, context)).strip()
        sources = tuple(job.link for job in _referenced_jobs(text, context.jobs))
        return Answer(text=text, sources=sources)
