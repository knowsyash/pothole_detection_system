"""SQLAlchemy database connection, engine initialization, and session management."""

import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger("okdriver.database")
logging.basicConfig(level=logging.INFO)

Base = declarative_base()


def get_engine():
    """Create database engine with automatic fallback to SQLite for local development."""
    primary_url = settings.DATABASE_URL
    try:
        # Test connecting to primary database (PostgreSQL)
        engine_args = {}
        if primary_url.startswith("sqlite"):
            engine_args["connect_args"] = {"check_same_thread": False}
        elif primary_url.startswith("postgresql"):
            # Pool configuration for PostgreSQL
            engine_args.update({
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
            })

        candidate_engine = create_engine(primary_url, **engine_args)
        # Attempt connection check with short timeout
        with candidate_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected to primary database: {primary_url.split('@')[-1] if '@' in primary_url else primary_url}")
        return candidate_engine

    except Exception as exc:
        if settings.ENABLE_SQLITE_FALLBACK:
            logger.warning(
                f"Failed to connect to primary database ({exc}). "
                f"Falling back to local SQLite at {settings.SQLITE_FALLBACK_URL}"
            )
            fallback_engine = create_engine(
                settings.SQLITE_FALLBACK_URL,
                connect_args={"check_same_thread": False},
            )
            return fallback_engine
        else:
            logger.error(f"Failed to connect to database at {primary_url}: {exc}")
            raise exc


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables if they do not exist."""
    import app.models.pothole  # Ensure models are imported
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized.")


# Auto-create tables on module load
try:
    init_db()
except Exception as _e:
    logger.warning(f"Could not auto-initialize tables on startup: {_e}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

