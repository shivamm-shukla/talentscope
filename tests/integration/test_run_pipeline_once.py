import pytest

from workers import run_pipeline_once


def test_main_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit, match="DATABASE_URL must be set"):
        run_pipeline_once.main()


def test_main_runs_pipeline_once_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'pipeline_once.db'}"
    )
    calls = []
    monkeypatch.setattr(
        run_pipeline_once,
        "run_pipeline",
        lambda session_factory, sources: calls.append(sources),
    )

    run_pipeline_once.main()

    assert len(calls) == 1
    assert [source.name for source in calls[0]] == ["internshala", "remotive"]
