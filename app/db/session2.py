"""Database session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting a database session.

    Yields:
        Database session that is automatically closed when done.

    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
