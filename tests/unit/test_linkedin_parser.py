import io
import zipfile

import pytest

from integrations.linkedin.parser import (
    LinkedinExportInvalid,
    LinkedinExportTooLarge,
    parse_export,
)


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


POSITIONS_CSV = (
    "Company Name,Title,Description,Location,Started On,Finished On\n"
    "Example Co,Python Intern,Built a Flask API,Remote,Jan 2026,\n"
)
SKILLS_CSV = "Name\nExcel\nFigma\n"
EDUCATION_CSV = (
    "School Name,Degree Name,Notes,Start Date,End Date\n" "Some University,B.Tech,,,\n"
)
PROFILE_CSV = "First Name,Last Name,Headline\nJane,Doe,Backend developer\n"


def test_parse_export_reads_known_files() -> None:
    archive = _zip_bytes(
        {
            "Positions.csv": POSITIONS_CSV,
            "Skills.csv": SKILLS_CSV,
            "Education.csv": EDUCATION_CSV,
            "Profile.csv": PROFILE_CSV,
        }
    )

    export = parse_export(archive)

    assert export.headline == "Backend developer"
    assert export.positions[0].title == "Python Intern"
    assert export.positions[0].company == "Example Co"
    assert export.positions[0].description == "Built a Flask API"
    assert export.education == ("Some University, B.Tech",)
    assert export.skills == ("Excel", "Figma")


def test_parse_export_tolerates_missing_files() -> None:
    archive = _zip_bytes({"Skills.csv": SKILLS_CSV})

    export = parse_export(archive)

    assert export.skills == ("Excel", "Figma")
    assert export.positions == ()
    assert export.headline == ""


def test_parse_export_ignores_unknown_files() -> None:
    archive = _zip_bytes({"readme.txt": "hello"})

    export = parse_export(archive)

    assert export == parse_export(_zip_bytes({}))


def test_parse_export_rejects_invalid_zip() -> None:
    with pytest.raises(LinkedinExportInvalid):
        parse_export(b"not a zip file")


def test_parse_export_rejects_oversized_entry() -> None:
    archive = _zip_bytes({"Skills.csv": "Name\n" + "a" * (6 * 1024 * 1024)})

    with pytest.raises(LinkedinExportTooLarge):
        parse_export(archive)
