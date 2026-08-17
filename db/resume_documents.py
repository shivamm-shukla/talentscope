"""Persistence operations for generated resume versions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import ResumeDocument, User


def create_draft(
    session: Session,
    user: User,
    content: str,
    sections: dict,
    source_snapshot: dict,
) -> ResumeDocument:
    """Start a new resume version as an editable draft."""
    latest_version = session.scalar(
        select(ResumeDocument.version)
        .where(ResumeDocument.user_id == user.id)
        .order_by(ResumeDocument.version.desc())
        .limit(1)
    )
    draft = ResumeDocument(
        user=user,
        version=(latest_version or 0) + 1,
        content=content,
        sections=sections,
        is_final=False,
        source_snapshot=source_snapshot,
    )
    session.add(draft)
    return draft


def update_draft_sections(
    session: Session, resume: ResumeDocument, sections: dict
) -> ResumeDocument:
    """Overwrite a non-final draft's sections in place."""
    if resume.is_final:
        raise ValueError("cannot edit a finalized resume version")
    resume.sections = sections
    return resume


def finalize(session: Session, resume: ResumeDocument) -> ResumeDocument:
    """Lock a draft in as a saved version."""
    resume.is_final = True
    return resume


def latest_for_user(session: Session, user: User) -> ResumeDocument | None:
    return session.scalar(
        select(ResumeDocument)
        .where(ResumeDocument.user_id == user.id)
        .order_by(ResumeDocument.version.desc())
        .limit(1)
    )


def list_versions(session: Session, user: User) -> list[ResumeDocument]:
    return list(
        session.scalars(
            select(ResumeDocument)
            .where(ResumeDocument.user_id == user.id)
            .order_by(ResumeDocument.version.desc())
        ).all()
    )
