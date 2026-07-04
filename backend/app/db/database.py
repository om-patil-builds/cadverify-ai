import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("PostgreSQL Connected Successfully")
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Failed to connect to PostgreSQL: %s", exc)
