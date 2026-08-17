"""Standalone process that runs the Phase B pipeline on a cron schedule.

Runs independently of the Flask web process (see ARCHITECTURE.md's scheduler
topology decision) so a stuck scrape or notify run can't affect web uptime,
and vice versa.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from core.interfaces import JobSource, Notifier
from core.logging import configure_json_logging
from db.session import create_engine_and_session
from notifications.registry import create_notifier
from sources.registry import create_source
from workers import (
    run_analyze,
    run_github_sync,
    run_match,
    run_notify,
    run_remind,
    run_scrape,
)

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_NAMES = ("internshala", "remotive")
DEFAULT_CRON = "0 */2 * * *"

Stage = tuple[str, Callable[[Session], object]]


def _stages(
    sources: Iterable[JobSource],
    notifier_factory: Callable[[str], Notifier],
    github_token: str | None,
) -> tuple[Stage, ...]:
    sources = tuple(sources)
    return (
        ("scrape", lambda session: run_scrape.run(sources, session)),
        ("analyze", lambda session: run_analyze.run(session)),
        ("github_sync", lambda session: run_github_sync.run(session, github_token)),
        ("match", lambda session: run_match.run(session)),
        ("notify", lambda session: run_notify.run(session, notifier_factory)),
        ("remind", lambda session: run_remind.run(session, notifier_factory)),
    )


def run_pipeline(
    session_factory: Callable[[], Session],
    sources: Iterable[JobSource],
    notifier_factory: Callable[[str], Notifier] = create_notifier,
    github_token: str | None = None,
) -> None:
    """Run scrape, analyze, github_sync, match, notify, and remind in sequence.

    Each stage runs in its own transaction and its own try/except: a failure in
    one stage is logged and skipped rather than aborting the rest of the
    pipeline, matching the per-stage failure isolation ARCHITECTURE.md commits to.
    """
    for name, stage in _stages(sources, notifier_factory, github_token):
        try:
            with session_factory() as session:
                result = stage(session)
            logger.info("stage %s completed: %s", name, result)
        except Exception:
            logger.exception("stage %s failed; continuing to next stage", name)


def main() -> None:
    configure_json_logging()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be set")

    engine, session_factory = create_engine_and_session(database_url)
    cron_expression = os.environ.get("PIPELINE_CRON", DEFAULT_CRON)
    source_names = os.environ.get("PIPELINE_SOURCES")
    sources = [
        create_source(name)
        for name in (source_names.split(",") if source_names else DEFAULT_SOURCE_NAMES)
    ]

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_pipeline,
        CronTrigger.from_crontab(cron_expression),
        args=[
            session_factory,
            sources,
            create_notifier,
            os.environ.get("GITHUB_TOKEN"),
        ],
        id="santa-pipeline",
        max_instances=1,
        coalesce=True,
    )
    logger.info("Scheduler started with cron '%s'", cron_expression)
    try:
        scheduler.start()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
