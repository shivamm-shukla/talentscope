from analysis.resume_builder import build_resume_draft


def test_build_resume_draft_with_full_profile_data() -> None:
    sections = build_resume_draft(
        skills=["Python", "React"],
        headline="Aspiring backend engineer",
        positions=[
            {"title": "Intern", "company": "Acme", "description": "Built APIs"},
        ],
        education=["B.Tech CSE"],
        certifications=["AWS Cloud Practitioner"],
        languages=["Python", "JavaScript"],
        repo_count=12,
    )

    assert sections["summary"]["bullets"] == [
        "Aspiring backend engineer",
        "Skilled in Python, React.",
    ]
    assert sections["skills"]["bullets"] == ["Python", "React"]
    assert sections["projects"]["bullets"] == [
        "12 public GitHub repositories across Python, JavaScript"
    ]
    assert sections["experience"]["bullets"] == ["Intern at Acme — Built APIs"]
    assert sections["education"]["bullets"] == ["B.Tech CSE"]
    assert sections["certifications"]["bullets"] == ["AWS Cloud Practitioner"]


def test_build_resume_draft_with_no_synced_data_still_returns_usable_sections() -> None:
    sections = build_resume_draft()

    assert sections["summary"]["bullets"] == []
    assert sections["skills"]["bullets"] == []
    assert sections["projects"]["bullets"] == []
    assert sections["experience"]["bullets"] == []
    assert sections["education"]["bullets"] == []
    assert "certifications" not in sections


def test_position_without_description_or_company_still_produces_a_bullet() -> None:
    sections = build_resume_draft(positions=[{"title": "Freelancer"}])

    assert sections["experience"]["bullets"] == ["Freelancer"]


def test_position_missing_entirely_is_skipped() -> None:
    sections = build_resume_draft(positions=[{}])

    assert sections["experience"]["bullets"] == []
