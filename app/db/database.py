"""
Database connection and session management module.

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI route handlers.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger("database")


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all models."""
    pass


def _get_engine():
    """Create and configure the SQLAlchemy engine."""
    settings = get_settings()
    db_url = settings.database_url

    # Ensure data directory exists for SQLite
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    engine = create_engine(
        db_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        pool_pre_ping=True,
    )

    # Enable WAL mode for better SQLite concurrency
    if "sqlite" in db_url:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Module-level engine and session factory
engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables. Call on application startup."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Yields:
        SQLAlchemy Session instance.

    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
