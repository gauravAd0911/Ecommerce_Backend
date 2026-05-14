"""Database session dependency for FastAPI."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it after request."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

