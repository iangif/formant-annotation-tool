"""
Database setup.

This file defines:
1. The SQLAlchemy engine 
2. SessionLocal factory
3. The Base class for SQLAlchemy models
4. get_db(), used by FastAPI routes
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import FORMANT_DB_URL

# Manages database connections
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} # required for FastAPI
)

# Factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# All SQLAlchemy models inherit from this class in models.py
class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()