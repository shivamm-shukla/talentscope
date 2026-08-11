from sqlalchemy import text

from db.session import create_engine_and_session


def test_session_factory_uses_supplied_database_url() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")

    with session_factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1

    engine.dispose()
