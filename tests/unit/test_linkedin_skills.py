from analysis.linkedin_skills import infer_skills
from core.models import LinkedinExport, LinkedinPosition


def test_infer_skills_matches_vocabulary_across_export_fields() -> None:
    export = LinkedinExport(
        headline="Backend developer",
        positions=(
            LinkedinPosition(
                title="Python Intern",
                company="Example Co",
                description="Built a Flask API.",
            ),
        ),
        education=("Some University, B.Tech",),
        certifications=(),
        skills=(),
    )

    assert infer_skills(export) == ["python", "flask"]


def test_infer_skills_unions_raw_linkedin_skills() -> None:
    export = LinkedinExport(skills=("Excel", "Figma"))

    assert infer_skills(export) == ["Excel", "Figma"]


def test_infer_skills_does_not_duplicate_overlapping_skills() -> None:
    export = LinkedinExport(
        positions=(LinkedinPosition(title="Python Intern"),),
        skills=("python", "SQL"),
    )

    assert infer_skills(export) == ["python", "SQL"]
