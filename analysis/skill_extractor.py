"""Deterministic vocabulary-based skill extraction."""

import re

KNOWN_SKILLS = (
    "python",
    "sql",
    "flask",
    "django",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "java",
    "c++",
    "machine learning",
    "data analysis",
    "excel",
    "figma",
)


def extract_skills(text: str) -> list[str]:
    """Return known skills found in *text*, ordered by the canonical vocabulary."""
    normalized = text.casefold()
    return [
        skill
        for skill in KNOWN_SKILLS
        if re.search(rf"(?<![\w+#.]){re.escape(skill)}(?![\w+#.])", normalized)
    ]
