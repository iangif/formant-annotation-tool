"""
Imports token assignments from data/token_assignments.csv into SQLite.

Run from project root: uv run python -m scripts.import_assignments
"""

import csv
from pathlib import Path

from app.database import SessionLocal
from app.models import TokenAssignment

from scripts.utils import empty_to_none

CSV_PATH = Path("data/token_assignments.csv")

def to_bool(value: str | None) -> bool:
    """
    Helper to convert common CSV boolean strings into Python booleans.
    Accepted true values:
        true, 1, yes, y
    """

    value = empty_to_none(value)

    if value is None:
        return False

    return value.lower() in {"true", "1", "yes", "y"}

def main() -> None:
    """
    Imports all token assignments from the CSV file.
    """

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Could not find {CSV_PATH}")

    db = SessionLocal()

    try:
        with CSV_PATH.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            count = 0

            for row in reader:
                assignment = TokenAssignment(
                    token_id=row["token_id"],
                    annotator_id=row["annotator_id"],
                    batch_name=empty_to_none(row.get("batch_name")),
                    is_overlap=to_bool(row.get("is_overlap")),
                )

                db.add(assignment)
                count += 1

        db.commit()

        print(f"Imported {count} assignments from {CSV_PATH}")
    
    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    main()