"""One-shot entrypoint for running the pipeline from an external scheduler.

Unlike `workers/scheduler.py` (a long-running process with its own cron
loop), this runs scrape -> analyze -> match -> notify exactly once and exits,
for use from a scheduler that already provides the cron trigger — e.g. a
GitHub Actions scheduled workflow, where each run is a fresh process.
"""

from __future__ import annotations

import logging
import os

from core.logging import configure_json_logging
from db.session import create_engine_and_session
from sources.registry import create_source
from workers.scheduler import DEFAULT_SOURCE_NAMES, run_pipeline

logger = logging.getLogger(__name__)


def main() -> None:
    configure_json_logging()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be set")

    source_names = os.environ.get("PIPELINE_SOURCES")
    sources = [
        create_source(name)
        for name in (source_names.split(",") if source_names else DEFAULT_SOURCE_NAMES)
    ]

    engine, session_factory = create_engine_and_session(database_url)
    try:
        run_pipeline(
            session_factory, sources, github_token=os.environ.get("GITHUB_TOKEN")
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
