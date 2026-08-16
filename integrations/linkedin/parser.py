"""Parser for LinkedIn's self-service data export ("Get a copy of your data").

The export is a ZIP of CSVs the user downloads from LinkedIn's own privacy
settings and uploads here voluntarily. Everything here is defensive about the
untrusted input: only known filenames are read, nothing is ever extracted to
disk, and both per-file and per-row sizes are capped so a small malicious zip
can't turn into a memory or CPU bomb.
"""

from __future__ import annotations

import csv
import io
import zipfile

from core.models import LinkedinExport, LinkedinPosition

MAX_ENTRY_BYTES = 5 * 1024 * 1024
MAX_ROWS_PER_FILE = 2000

_KNOWN_FILES = {
    "positions.csv",
    "skills.csv",
    "education.csv",
    "profile.csv",
    "certifications.csv",
}


class LinkedinExportInvalid(Exception):
    """Raised when the uploaded file isn't a readable LinkedIn export."""


class LinkedinExportTooLarge(Exception):
    """Raised when a file inside the export exceeds the per-entry size cap."""


def _entries_by_name(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    matched: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        basename = info.filename.rsplit("/", 1)[-1].casefold()
        if basename in _KNOWN_FILES:
            matched[basename] = info
    return matched


def _read_rows(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> list[dict[str, str]]:
    if info.file_size > MAX_ENTRY_BYTES:
        raise LinkedinExportTooLarge(f"{info.filename} exceeds the size limit")
    with archive.open(info) as handle:
        text = io.TextIOWrapper(handle, encoding="utf-8-sig", errors="replace")
        reader = csv.DictReader(text)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= MAX_ROWS_PER_FILE:
                break
        return rows


def parse_export(file_bytes: bytes) -> LinkedinExport:
    """Parse a LinkedIn data-export ZIP into a `LinkedinExport`.

    Missing files (an older or partial export) are tolerated — only an
    unreadable zip is treated as an error.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile as error:
        raise LinkedinExportInvalid("uploaded file is not a valid zip") from error

    with archive:
        entries = _entries_by_name(archive)

        headline = ""
        if "profile.csv" in entries:
            rows = _read_rows(archive, entries["profile.csv"])
            if rows:
                headline = rows[0].get("Headline", "").strip()

        positions: list[LinkedinPosition] = []
        if "positions.csv" in entries:
            for row in _read_rows(archive, entries["positions.csv"]):
                positions.append(
                    LinkedinPosition(
                        title=row.get("Title", "").strip(),
                        company=row.get("Company Name", "").strip(),
                        description=row.get("Description", "").strip(),
                    )
                )

        education: list[str] = []
        if "education.csv" in entries:
            for row in _read_rows(archive, entries["education.csv"]):
                school = row.get("School Name", "").strip()
                degree = row.get("Degree Name", "").strip()
                label = ", ".join(part for part in (school, degree) if part)
                if label:
                    education.append(label)

        certifications: list[str] = []
        if "certifications.csv" in entries:
            for row in _read_rows(archive, entries["certifications.csv"]):
                name = row.get("Name", "").strip()
                if name:
                    certifications.append(name)

        skills: list[str] = []
        if "skills.csv" in entries:
            for row in _read_rows(archive, entries["skills.csv"]):
                name = row.get("Name", "").strip()
                if name:
                    skills.append(name)

    return LinkedinExport(
        headline=headline,
        positions=tuple(positions),
        education=tuple(education),
        certifications=tuple(certifications),
        skills=tuple(skills),
    )
