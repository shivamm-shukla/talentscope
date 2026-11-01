"""Gemini-backed QAEngine implementation."""

from __future__ import annotations

from collections.abc import Callable

from core.models import Answer, JobPosting, QueryContext

GenerateFn = Callable[[str], str]

# Below gunicorn's 60s worker timeout, so a slow call fails as a normal
# error (502 to the user) instead of the worker being killed. Also sent to
# Gemini as the server-side deadline.
GEMINI_TIMEOUT_MS = 45_000
# Briefs are 3-5 sentences and resumes about a page; capping output keeps
# latency predictable.
GEMINI_MAX_OUTPUT_TOKENS = 2048


def _thinking_options(types) -> list[object | None]:
    """Ways to keep "thinking" short, most effective first.

    Thinking models spend many seconds reasoning before they write — enough
    to blow the deadline on a 5-sentence brief. Models differ in what they
    accept (2.x: a token budget, 3.x: a level), so try each and fall back to
    the model default if neither is supported.
    """
    return [
        types.ThinkingConfig(thinking_budget=0),
        types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        None,
    ]


def _is_thinking_rejection(error: Exception) -> bool:
    return getattr(error, "code", None) == 400 and "think" in str(error).lower()


def gemini_generate(api_key: str, model: str) -> GenerateFn:
    """Build a generate function that calls the real Gemini API on demand.

    Uses the `google-genai` SDK (plain HTTPS). The old `google-generativeai`
    SDK is end-of-life and talked gRPC, which hung on Render until gunicorn
    killed the worker — every AI feature failed with no response.
    """
    state: dict[str, object] = {}

    def generate(prompt: str) -> str:
        from google import genai
        from google.genai import errors, types

        if "client" not in state:
            state["client"] = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
            )
            state["options"] = _thinking_options(types)
        client = state["client"]
        options = state["options"]
        while True:
            thinking = options[0]
            config = types.GenerateContentConfig(
                max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                **({"thinking_config": thinking} if thinking is not None else {}),
            )
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
            except errors.ClientError as error:
                # Remember what this model rejects so later calls skip it.
                if thinking is not None and _is_thinking_rejection(error):
                    options.pop(0)
                    continue
                raise
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
