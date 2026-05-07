"""
Create the SQLite database tables

Run from project root: uv run python -m scripts.init_db
"""

from app.database import Base, engine
from app import models

def main():
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

if __name__ == "__main__":
    main()