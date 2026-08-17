"""Turns a company's known postings into a short research brief via an LLM.

Same shape as ai/resume_prompt.py: calls the provider-agnostic
``GenerateFn`` directly rather than going through the scout-shaped
``QAEngine`` Protocol, since a brief is a fixed-shape document, not a
free-form Q&A turn.
"""

from __future__ import annotations

from ai.providers.gemini import GenerateFn

MAX_DESCRIPTION_CHARS = 1200


def _build_prompt(company: str, descriptions: list[str]) -> str:
    lines = [
        "You are santa scout's company research assistant.",
        "Write a short, factual brief (3-5 sentences) for a student "
        "considering applying to this company, based only on the posting "
        "text below. Do not invent facts that aren't present in the text. "
        "If the text doesn't say much about the company itself, say so "
        "plainly instead of guessing.",
        "",
        f"Company: {company}",
        "",
        "Posting text:",
    ]
    if descriptions:
        for text in descriptions:
            lines.append(f"- {text[:MAX_DESCRIPTION_CHARS]}")
    else:
        lines.append("(no posting text available)")
    return "\n".join(lines)


def generate_company_brief(
    generate: GenerateFn, company: str, descriptions: list[str]
) -> str:
    return generate(_build_prompt(company, descriptions)).strip()
