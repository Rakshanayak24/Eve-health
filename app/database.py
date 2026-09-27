from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    # Needed for SQLite when used across threads (used in the test suite).
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and guarantees it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
