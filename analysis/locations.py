"""Location normalization: city aliases, multi-city postings, remote work.

Postings and users spell the same place differently ("Bangalore" vs
"Bengaluru", "Work From Home" vs "Remote"), and a posting often lists several
cities in one field. Matching compares canonical names, never raw strings.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

REMOTE = "remote"

# alias -> canonical. Keys are casefolded; canonical names are what the UI
# offers as location chips (lowercased here).
_ALIASES = {
    "bengaluru": "bangalore",
    "bangalore urban": "bangalore",
    "gurugram": "gurgaon",
    "new delhi": "delhi",
    "delhi ncr": "delhi",
    "ncr": "delhi",
    "bombay": "mumbai",
    "navi mumbai": "mumbai",
    "madras": "chennai",
    "calcutta": "kolkata",
    "poona": "pune",
    "secunderabad": "hyderabad",
    "greater noida": "noida",
    "work from home": REMOTE,
    "wfh": REMOTE,
    "anywhere": REMOTE,
    "worldwide": REMOTE,
    "remote": REMOTE,
}

_SEPARATORS = re.compile(r"[,/|;]|\s+(?:and|or|&)\s+")


def canonical_location(name: str) -> str:
    """Canonical casefolded name for one place ("Bengaluru " -> "bangalore")."""
    key = " ".join(name.casefold().split())
    key = key.removeprefix("remote - ").removeprefix("remote-")
    return _ALIASES.get(key, key)


def location_set(raw: str) -> set[str]:
    """Every canonical place named in a posting's location field.

    "Bangalore, Karnataka" yields {"bangalore", "karnataka"} — the extra
    state token is harmless since a user preference never names a state
    unless they meant it.
    """
    return {
        canonical_location(part)
        for part in _SEPARATORS.split(raw or "")
        if part.strip()
    }


def location_matches(
    desired: Iterable[str], job_location: str, work_mode: str | None = None
) -> bool:
    """True when the posting is in any desired place (or no place is desired).

    "remote" in the preferences also matches a posting classified as remote
    work, whatever its location field says.
    """
    wanted = {canonical_location(place) for place in desired if place.strip()}
    if not wanted:
        return True
    places = location_set(job_location)
    if work_mode == REMOTE:
        places.add(REMOTE)
    return bool(wanted & places)
