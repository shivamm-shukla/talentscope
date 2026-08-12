from sqlalchemy import text

from db.session import create_engine_and_session, normalize_database_url


def test_session_factory_uses_supplied_database_url() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")

    with session_factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1

    engine.dispose()


def test_normalize_database_url_forces_psycopg_driver() -> None:
    assert normalize_database_url("postgresql://u:p@host/db") == (
        "postgresql+psycopg://u:p@host/db"
    )
    assert normalize_database_url("postgres://u:p@host/db") == (
        "postgresql+psycopg://u:p@host/db"
    )


def test_normalize_database_url_leaves_other_schemes_untouched() -> None:
    assert (
        normalize_database_url("sqlite:///talentscope.db") == "sqlite:///talentscope.db"
    )
    assert (
        normalize_database_url("postgresql+psycopg://u:p@host/db")
        == "postgresql+psycopg://u:p@host/db"
    )
