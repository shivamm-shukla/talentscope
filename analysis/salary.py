"""Stipend normalization helpers."""

import re


def normalize_monthly_stipend(salary_raw: str | None) -> int | None:
    """Extract a monthly INR stipend when the amount is unambiguous."""
    if not salary_raw:
        return None
    text = salary_raw.casefold().replace(",", "")
    if "unpaid" in text or "negotiable" in text:
        return None
    match = re.search(r"(?:₹|inr|rs\.?\s*)?\s*(\d+(?:\.\d+)?)\s*(k|lakh)?", text)
    if not match:
        return None
    amount = float(match.group(1))
    multiplier = {"k": 1_000, "lakh": 100_000}.get(match.group(2), 1)
    value = int(amount * multiplier)
    if "per annum" in text or "/year" in text or "yearly" in text:
        return value // 12
    return value
