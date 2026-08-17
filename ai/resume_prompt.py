"""Turns a structured resume draft into polished text via an LLM.

Calls the provider-agnostic ``GenerateFn`` directly (see
``ai/providers/gemini.py``) rather than going through the scout-shaped
``QAEngine`` Protocol, since resume generation isn't a question-answering
task.
"""

from __future__ import annotations

from ai.providers.gemini import GenerateFn


def _build_prompt(name: str, sections: dict[str, dict[str, object]]) -> str:
    lines = [
        "You are santa resume's assistant.",
        "Write a concise, ATS-friendly resume in plain text from the structured "
        "data below. Do not invent facts that aren't present in the data.",
        "",
        f"Candidate: {name or 'Student'}",
        "",
    ]
    for section in sections.values():
        heading = section.get("heading", "")
        bullets = section.get("bullets") or []
        lines.append(f"{heading}:")
        lines.extend(f"- {bullet}" for bullet in bullets)
        if not bullets:
            lines.append("(not provided)")
        lines.append("")
    return "\n".join(lines)


def generate_resume_content(
    generate: GenerateFn, name: str, sections: dict[str, dict[str, object]]
) -> str:
    return generate(_build_prompt(name, sections)).strip()
