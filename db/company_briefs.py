"""Persistence for cached, generated company research briefs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import CompanyBrief


def _normalize(company: str) -> str:
    return company.strip().casefold()


def get_cached(session: Session, company: str) -> CompanyBrief | None:
    return session.scalar(
        select(CompanyBrief).where(CompanyBrief.company == _normalize(company))
    )


def upsert(session: Session, company: str, content: str) -> CompanyBrief:
    brief = get_cached(session, company)
    if brief is None:
        brief = CompanyBrief(company=_normalize(company), content=content)
        session.add(brief)
    else:
        brief.content = content
        brief.generated_at = datetime.now(UTC)
    return brief
