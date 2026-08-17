"""Relational persistence model for Santa's job-matching pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from flask_login import UserMixin
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for every Santa ORM model."""


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "source", "title", "company", "location", name="uq_jobs_source_identity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    salary_raw: Mapped[str | None] = mapped_column(String(255))
    salary_numeric: Mapped[int | None] = mapped_column(Integer)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    listing_type: Mapped[str | None] = mapped_column(String(32))
    work_mode: Mapped[str | None] = mapped_column(String(32))
    pay_type: Mapped[str | None] = mapped_column(String(32))
    duration_months: Mapped[int | None] = mapped_column(Integer)
    target_year: Mapped[str | None] = mapped_column(String(16))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    matches: Mapped[list[Match]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    observations: Mapped[list[JobObservation]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class User(UserMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64))
    github_username: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    preferences: Mapped[UserPreference | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    github_profile: Mapped[GithubProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    linkedin_profile: Mapped[LinkedinProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    matches: Mapped[list[Match]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications_sent: Mapped[list[NotificationSent]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    actions: Mapped[list[ActionLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resume_documents: Mapped[list[ResumeDocument]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    locations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    minimum_stipend: Mapped[int | None] = mapped_column(Integer)
    preferred_channels: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    user: Mapped[User] = relationship(back_populates="preferences")


class GithubProfile(Base):
    """Latest synced snapshot of a user's public GitHub activity.

    Kept as a stored snapshot (not fetched live on demand) so a later resume
    feature can reuse it without re-hitting GitHub's API.
    """

    __tablename__ = "github_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    repo_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    inferred_skills: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="github_profile")


class LinkedinProfile(Base):
    """Latest imported snapshot of a user's LinkedIn data export.

    Populated from a user-uploaded export (LinkedIn has no usable public API),
    kept as a structured snapshot for a later resume feature to reuse.
    """

    __tablename__ = "linkedin_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    headline: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    positions: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    education: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    certifications: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    inferred_skills: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="linkedin_profile")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_matches_user_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="matches")
    job: Mapped[Job] = relationship(back_populates="matches")
    notifications_sent: Mapped[list[NotificationSent]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class NotificationSent(Base):
    __tablename__ = "notifications_sent"
    __table_args__ = (
        UniqueConstraint("match_id", "channel", name="uq_notifications_match_channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="notifications_sent")
    match: Mapped[Match] = relationship(back_populates="notifications_sent")


class ActionLog(Base):
    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User | None] = relationship(back_populates="actions")


class ResumeDocument(Base):
    """A generated resume version for a user.

    Versioned (not overwrite-in-place) so a user can compare/revert past
    generations. Within a version, ``is_final`` distinguishes an editable
    draft (fresh off generation, or mid-edit) from a version the user has
    locked in.
    """

    __tablename__ = "resume_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_resume_documents_user_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="resume_documents")


APPLICATION_STATUSES = (
    "saved",
    "applied",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
)


class Application(Base):
    """A user's tracked application status for a specific job.

    ``status_history`` is an append-only log of past transitions kept
    inline (rather than a separate history table) since it's small and
    always read alongside the current status.
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="saved")
    status_history: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship(back_populates="applications")


class JobObservation(Base):
    """One row per scrape cycle a job was actually seen in.

    An append-only log rather than a mutable counter, so ghost-job
    detection can look at gaps between observations (a posting that
    vanished for a cycle and reappeared) rather than just a total count.
    """

    __tablename__ = "job_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    job: Mapped[Job] = relationship(back_populates="observations")
