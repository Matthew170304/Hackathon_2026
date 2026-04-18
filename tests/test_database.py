from sqlalchemy import inspect

from app.db.database import create_database_tables, create_engine_from_settings, get_db_session


def test_create_database_tables_creates_expected_tables() -> None:
    test_engine = create_engine_from_settings("sqlite://")
    create_database_tables(test_engine)

    table_names = set(inspect(test_engine).get_table_names())

    assert "incidents" in table_names
    assert "processed_incidents" in table_names
    assert "upload_batches" in table_names


def test_get_db_session_yields_session() -> None:
    session_generator = get_db_session()
    session = next(session_generator)

    assert session is not None

    try:
        next(session_generator)
    except StopIteration:
        pass
