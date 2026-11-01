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


def _fake_genai(monkeypatch, reject=()):
    """Patch google.genai.Client; the fake model rejects thinking configs whose
    kind is listed in *reject* (``"budget"`` / ``"level"``) like a real 400."""
    from google import genai
    from google.genai import errors

    calls = {"clients": [], "configs": []}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            thinking = config.thinking_config
            calls["configs"].append(thinking)
            kind = None
            if thinking is not None:
                kind = "budget" if thinking.thinking_budget is not None else "level"
            if kind in reject:
                raise errors.ClientError(
                    400,
                    {"error": {"code": 400, "message": f"Thinking {kind} unsupported"}},
                )
            return type("Resp", (), {"text": f"{model}:{contents}"})()

    class FakeClient:
        def __init__(self, *, api_key, http_options):
            calls["clients"].append((api_key, http_options.timeout))
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)
    return calls


def test_gemini_generate_uses_one_http_client_with_timeout(monkeypatch) -> None:
    from ai.providers import gemini

    calls = _fake_genai(monkeypatch)
    generate = gemini.gemini_generate("key-123", "gemini-flash-latest")

    assert generate("hello") == "gemini-flash-latest:hello"
    assert generate("again") == "gemini-flash-latest:again"
    assert calls["clients"] == [("key-123", gemini.GEMINI_TIMEOUT_MS)]
    assert gemini.GEMINI_TIMEOUT_MS < 60_000  # gunicorn --timeout 60
    assert calls["configs"][0].thinking_budget == 0


def test_gemini_generate_falls_back_when_model_rejects_thinking_settings(
    monkeypatch,
) -> None:
    from ai.providers import gemini

    calls = _fake_genai(monkeypatch, reject=("budget",))
    generate = gemini.gemini_generate("k", "gemini-3-flash")

    assert generate("one") == "gemini-3-flash:one"
    assert calls["configs"][0].thinking_budget == 0
    assert calls["configs"][1].thinking_level is not None
    # The rejection is remembered: the next call goes straight to the level.
    generate("two")
    assert len(calls["configs"]) == 3
    assert calls["configs"][2].thinking_level is not None


def test_gemini_generate_drops_thinking_config_if_nothing_is_supported(
    monkeypatch,
) -> None:
    from ai.providers import gemini

    calls = _fake_genai(monkeypatch, reject=("budget", "level"))

    assert gemini.gemini_generate("k", "m")("x") == "m:x"
    assert calls["configs"][-1] is None


def test_company_brief_prompt_caps_the_number_of_postings() -> None:
    from ai.company_brief_prompt import MAX_DESCRIPTIONS, _build_prompt

    prompt = _build_prompt("Acme", [f"posting {i}" for i in range(30)])

    assert f"posting {MAX_DESCRIPTIONS - 1}" in prompt
    assert f"posting {MAX_DESCRIPTIONS}\n" not in prompt + "\n"
