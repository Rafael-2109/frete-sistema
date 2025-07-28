"""
Database configuration and session management
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from typing import Generator
from contextlib import contextmanager
import logging

from ..core.settings import settings

logger = logging.getLogger(__name__)

# Database naming conventions
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

# Create base class for models
Base = declarative_base(metadata=metadata)

# Database engine (only created if DATABASE_URL is set)
engine = None
SessionLocal = None
db_session = None

if settings.DATABASE_URL:
    # Engine configuration with pool settings for production
    engine_args = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "echo": settings.DB_ECHO,
    }
    
    # SQLite specific args
    if settings.DATABASE_URL.startswith("sqlite"):
        engine_args["connect_args"] = {"check_same_thread": False}
    
    engine = create_engine(settings.DATABASE_URL, **engine_args)
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    
    # Scoped session for thread safety
    db_session = scoped_session(SessionLocal)
    
    logger.info("Database engine configured")
else:
    logger.warning("No DATABASE_URL configured, database features disabled")


def get_db() -> Generator[Session, None, None]:
    """
    Get database session
    """
    if SessionLocal is None:
        raise RuntimeError("Database not configured")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Provide a transactional scope for database operations
    """
    if SessionLocal is None:
        raise RuntimeError("Database not configured")
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database (create tables)
    """
    if engine is None:
        logger.warning("Cannot initialize database: no DATABASE_URL configured")
        return
    
    # Import all models to ensure they're registered
    from . import mcp_models  # noqa
    from . import mcp_session  # noqa
    from . import mcp_logs  # noqa
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def check_db_connection() -> bool:
    """
    Check if database connection is working
    """
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False