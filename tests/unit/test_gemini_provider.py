from ai.providers.gemini import GeminiQAEngine
from core.models import JobPosting, QueryContext


def test_gemini_engine_answers_with_context_job_sources() -> None:
    captured = {}

    def fake_generate(prompt: str) -> str:
        captured["prompt"] = prompt
        return "  There are 2 matching internships.  "

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

    assert answer.text == "There are 2 matching internships."
    assert answer.sources == ("https://example.test/jobs/1",)
    assert "How many Python internships are there?" in captured["prompt"]
    assert "Python Intern at Example Co" in captured["prompt"]


def test_gemini_engine_handles_empty_job_context() -> None:
    engine = GeminiQAEngine(generate=lambda prompt: "No jobs yet.")

    answer = engine.answer("Any jobs?", QueryContext())

    assert answer.text == "No jobs yet."
    assert answer.sources == ()
