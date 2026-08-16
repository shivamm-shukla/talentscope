"""Gemini-backed QAEngine implementation."""

from __future__ import annotations

from collections.abc import Callable

from core.models import Answer, QueryContext

GenerateFn = Callable[[str], str]


def gemini_generate(api_key: str, model: str) -> GenerateFn:
    """Build a generate function that calls the real Gemini API on demand."""

    def generate(prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        response = genai.GenerativeModel(model).generate_content(prompt)
        return response.text

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


class GeminiQAEngine:
    """Answers questions about persisted job data using Gemini."""

    def __init__(self, generate: GenerateFn) -> None:
        self._generate = generate

    def answer(self, question: str, context: QueryContext) -> Answer:
        text = self._generate(_build_prompt(question, context))
        return Answer(
            text=text.strip(), sources=tuple(job.link for job in context.jobs)
        )
