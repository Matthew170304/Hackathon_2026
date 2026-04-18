from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Base


def create_engine_from_settings(database_url: str | None = None) -> Engine:
    """
    Create SQLAlchemy engine from application settings.

    Args:
        database_url: optional override used by tests

    Returns:
        SQLAlchemy Engine.
    """
    settings = get_settings()
    url = database_url or settings.database_url
    connect_args = (
        {"check_same_thread": False}
        if url.startswith("sqlite")
        else {}
    )

    return create_engine(url, connect_args=connect_args)


engine = create_engine_from_settings()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database_tables(bind_engine: Engine | None = None) -> None:
    """
    Create database tables for local MVP development.
    """
    Base.metadata.create_all(bind=bind_engine or engine)


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Yields:
        SQLAlchemy Session.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
