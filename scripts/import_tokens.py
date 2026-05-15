"""
Imports token metadata from data/pilot_tokens.csv into SQLite.

Run from project root: uv run python -m scripts.import_tokens

1. Reads each CSV row
2. Creates / updates a Token row
3. Commits all rows at the end
"""

import csv
from pathlib import Path

from app.database import SessionLocal
from app.models import Token

from scripts.utils import empty_to_none

CSV_PATH = Path("data/pilot_tokens.csv")

def to_float(value: str | None) -> float | None:
    """
    Helper to convert a CSV value to float, or None if empty.
    """

    value = empty_to_none(value)

    if value is None:
        return None

    return float(value)

def to_int(value: str | None) -> int | None:
    """
    Helper to convert a CSV value to int, or None if empty.
    """

    value = empty_to_none(value)

    if value is None:
        return None

    return int(value)

def build_token(row: dict[str, str]) -> Token:
    """
    Convert one CSV row into a Token SQLAlchemy object.
    """

    return Token(
        id=row["id"],
        corpus=row["corpus"],
        speaker_id=empty_to_none(row.get("speaker_id")),
        vowel_label=row["vowel_label"],
        word=empty_to_none(row.get("word")),
        preceding_phone=empty_to_none(row.get("preceding_phone")),
        following_phone=empty_to_none(row.get("following_phone")),
        duration_ms=to_float(row.get("duration_ms")),
        min_max_formant=to_float(row.get("min_max_formant")),
        max_max_formant=to_float(row.get("max_max_formant")),
        n_formants=to_int(row.get("n_formants")),
        max_number_of_formants=to_float(row.get("max_number_of_formants")),
        n_candidates=to_int(row.get("n_candidates")) or 20,
        auto_winner_panel=to_int(row.get("auto_winner_panel")),
        image_path=row["image_path"],
        audio_path=empty_to_none(row.get("audio_path")),
        candidates_pickle_path=empty_to_none(row.get("candidates_pickle_path")),
    )

def main() -> None:
    """
    Imports all tokens from the CSV file.
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Could not find {CSV_PATH}")
    
    db = SessionLocal()

    try:
        with CSV_PATH.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            count = 0

            for row in reader:
                token = build_token(row)
                
                # Inserts if token_id does not exist
                # Updates if token_id already exists
                db.merge(token)

                count += 1
        
        db.commit()

        print(f"Imported {count} tokens from {CSV_PATH}")
    
    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    main()