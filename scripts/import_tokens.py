"""
Imports token metadata from data/common_pilot_0_49.csv into SQLite.

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

CSV_PATH = Path("data/common_pilot_0_49.csv")

def to_float(value: str | None) -> float | None:
    """
    Helper to convert a CSV value to float, or None if empty.
    """

    value = empty_to_none(value)
    return None if value is None else float(value)

def to_int(value: str | None) -> int | None:
    """
    Helper to convert a CSV value to int, or None if empty.
    """

    value = empty_to_none(value)
    return None if value is None else int(value)

def build_token_id(row: dict[str, str]) -> str:
    """
    Builds stable token id.
    """

    index = int(row["index"])
    padded_index = f"{index:05d}"

    return (
        f"{padded_index}_"
        f"{row['phone']}_"
        f"{row['speaker']}_"
        f"{row['gender']}_"
        f"{row['discourse']}_"
        f"{row['phone_begin']}"
    )

def build_token(row: dict[str, str]) -> Token:
    """
    Convert one CSV row into a Token SQLAlchemy object.
    """

    token_id = build_token_id(row)

    phone_begin = to_float(row.get("phone_begin"))
    phone_end = to_float(row.get("phone_end"))

    duration_ms = None
    if phone_begin is not None and phone_end is not None:
        duration_ms = round((phone_end - phone_begin) * 1000, 2)

    return Token(
        id=token_id,
        corpus="librispeech",
        speaker_id=empty_to_none(row.get("speaker")),
        vowel_label=row["phone"],
        word=empty_to_none(row.get("word")),
        preceding_phone=empty_to_none(row.get("previous_phone")),
        following_phone=empty_to_none(row.get("following_phone")),
        duration_ms=duration_ms,

        # Placeholders for now
        min_max_formant=None,
        max_max_formant=None,
        n_formants=None,
        max_number_of_formants=None,

        n_candidates=20,
        auto_winner_panel=to_int(row.get("winner_auto")) or 10,

        image_path=f"app/static/images/{token_id}.png",
        audio_path=f"app/static/audio/{token_id}.wav",
        textgrid_path=f"app/static/audio/{token_id}.TextGrid",
        candidates_pickle_path=None,
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