"""
Database setup.

This file defines:
1. The SQLite database location (based on .env)
2. The SQLAlchemy engine for managing the database connection
3. SessionLocal for managing database sessions
4. Base, which all SQLAlchemy models inherit from
5. get_db() for FastAPI routes to access the database
"""

from app.config import ANNOTATOR_ID

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite database file
# Location: data/{ANNOTATOR_ID}.sqlite, defaults to data/unknown.sqlite
DATABASE_URL = f"sqlite:///./data/{ANNOTATOR_ID}.sqlite"

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()