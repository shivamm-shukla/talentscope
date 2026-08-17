from db.company_briefs import get_cached, upsert
from db.models import Base
from db.session import create_engine_and_session


def test_get_cached_returns_none_when_absent() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        assert get_cached(session, "Acme") is None
    engine.dispose()


def test_upsert_then_get_cached_is_case_insensitive() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        upsert(session, "Acme", "A software company.")
        session.commit()

        cached = get_cached(session, "  ACME  ")

    engine.dispose()
    assert cached is not None
    assert cached.content == "A software company."


def test_upsert_refreshes_existing_brief_instead_of_duplicating() -> None:
    engine, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory() as session:
        first = upsert(session, "Acme", "Old content.")
        session.commit()
        first_id = first.id

        second = upsert(session, "acme", "New content.")
        session.commit()

    engine.dispose()
    assert second.id == first_id
    assert second.content == "New content."
