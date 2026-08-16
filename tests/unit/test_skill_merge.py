from analysis.skill_merge import merge_skills


def test_merge_skills_appends_new_entries_case_insensitively() -> None:
    merged = merge_skills(["SQL"], ["python", "sql", "flask"])

    assert merged == ["SQL", "python", "flask"]


def test_merge_skills_preserves_existing_order_and_casing() -> None:
    merged = merge_skills(["Python", "React"], [])

    assert merged == ["Python", "React"]


def test_merge_skills_handles_empty_existing() -> None:
    merged = merge_skills([], ["python", "sql"])

    assert merged == ["python", "sql"]
