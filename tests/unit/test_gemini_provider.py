from ai.providers.gemini import GeminiQAEngine
from core.models import JobPosting, QueryContext


def test_gemini_engine_answers_with_context_job_sources() -> None:
    captured = {}

    def fake_generate(prompt: str) -> str:
        captured["prompt"] = prompt
        return "  There's one match: Python Intern at Example Co.  "

    engine = GeminiQAEngine(generate=fake_generate)
    context = QueryContext(
        jobs=(
            JobPosting(
                source="fixture",
                title="Python Intern",
                company="Example Co",
                location="Remote",
                link="https://example.test/jobs/1",
            ),
        )
    )

    answer = engine.answer("How many Python internships are there?", context)

    assert answer.text == "There's one match: Python Intern at Example Co."
    assert answer.sources == ("https://example.test/jobs/1",)
    assert "How many Python internships are there?" in captured["prompt"]
    assert "Python Intern at Example Co" in captured["prompt"]


def test_gemini_engine_only_sources_jobs_the_answer_actually_mentions() -> None:
    """The prompt lists every job in context so Gemini can consider them all,
    but sources should reflect only what the answer is actually about — not
    every job that happened to be in the prompt."""
    engine = GeminiQAEngine(
        generate=lambda _prompt: "There's a strong Python Intern role available."
    )
    context = QueryContext(
        jobs=(
            JobPosting(
                source="fixture",
                title="Python Intern",
                company="Example Co",
                location="Remote",
                link="https://example.test/jobs/1",
            ),
            JobPosting(
                source="fixture",
                title="Marketing Intern",
                company="Other Co",
                location="Remote",
                link="https://example.test/jobs/2",
            ),
        )
    )

    answer = engine.answer("Any Python roles?", context)

    assert answer.sources == ("https://example.test/jobs/1",)


def test_gemini_engine_handles_empty_job_context() -> None:
    engine = GeminiQAEngine(generate=lambda prompt: "No jobs yet.")

    answer = engine.answer("Any jobs?", QueryContext())

    assert answer.text == "No jobs yet."
    assert answer.sources == ()
