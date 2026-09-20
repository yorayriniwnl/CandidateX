"""Database session and engine management."""

from collections.abc import Generator

# Engine configuration with dialect-specific options
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from cci.config import settings

engine_kwargs: dict[str, Any] = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
