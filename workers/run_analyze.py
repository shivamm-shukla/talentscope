"""Normalize stored jobs' stipends and backfill missing skill tags."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from analysis.salary import normalize_monthly_stipend
from analysis.skill_extractor import extract_skills
from db.models import Job
from db.session import create_engine_and_session


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    jobs_processed: int
    salary_normalized: int
    skills_backfilled: int


def run(session: Session) -> AnalyzeResult:
    """Normalize salary and backfill skills for every stored job, then commit."""
    jobs = list(session.scalars(select(Job)).all())
    salary_normalized = skills_backfilled = 0

    for job in jobs:
        if job.salary_numeric is None and job.salary_raw is not None:
            normalized = normalize_monthly_stipend(job.salary_raw)
            if normalized is not None:
                job.salary_numeric = normalized
                salary_normalized += 1

        if not job.skills:
            extracted = extract_skills(job.title)
            if extracted:
                job.skills = extracted
                skills_backfilled += 1

    session.commit()
    return AnalyzeResult(
        jobs_processed=len(jobs),
        salary_normalized=salary_normalized,
        skills_backfilled=skills_backfilled,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize stipends and backfill skills for stored jobs."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("provide --database-url or set DATABASE_URL")
    engine, session_factory = create_engine_and_session(arguments.database_url)
    try:
        with session_factory() as session:
            result = run(session)
        print(
            f"Processed {result.jobs_processed}; "
            f"normalized salary for {result.salary_normalized}; "
            f"backfilled skills for {result.skills_backfilled}."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
