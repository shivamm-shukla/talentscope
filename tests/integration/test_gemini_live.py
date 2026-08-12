import os

import pytest

from ai.registry import create_qa_engine
from core.models import JobPosting, QueryContext

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not configured"
)
def test_gemini_engine_answers_a_real_question() -> None:
    engine = create_qa_engine()
    context = QueryContext(
        jobs=(
            JobPosting(
                source="fixture",
                title="Python Intern",
                company="Example Co",
                location="Remote",
                link="https://example.test/jobs/1",
                skills=("python",),
            ),
        )
    )

    answer = engine.answer("Which internships use Python?", context)

    assert answer.text.strip()
