"""
Create/update the local SQLite database from locally synced batches.

Run from project root after scripts.sync_assigned_batches:
    uv run python -m scripts.sync_database

Safe to run repeatedly.
"""

from __future__ import annotations

import csv
from pathlib import Path
import yaml

from sqlalchemy import select

from app.config import ANNOTATOR_ID, CORPORA_DIR
from app.database import Base, SessionLocal, engine
from app.models import Assignment, Batch, Corpus, Token
from scripts.migrate_token_rendering_metadata import migrate_database, resolve_db_path
from scripts.utils import empty_to_none

def to_float(value: str | int | float | None) -> float | None:
    value = empty_to_none(value)
    return None if value is None else float(value)

def to_int(value: str | None, default: int) -> int:
    value = empty_to_none(value)
    return default if value is None else int(float(value))

def seconds_to_ms_label(value: str | None) -> str:
    seconds = to_float(value)
    if seconds is None:
        return "NA"
    return str(int(round(seconds * 1000)))

def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing corpus config YAML: {path}")

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def load_fasttrack_winners(path: Path) -> dict[str, int]:
    if not path.exists():
        raise FileNotFoundError(f"Missing local FastTrack CSV: {path}")

    winners: dict[str, int] = {}

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            file_stem = empty_to_none(row.get("file"))
            winner_auto = empty_to_none(row.get("winner_auto"))

            if file_stem is None or winner_auto is None:
                continue

            winners[file_stem] = int(float(winner_auto))

    return winners

def fasttrack_params_for_gender(config: dict, gender: str | None) -> dict:
    groups = config.get("groups", {})
    gender_key = (gender or "").lower()

    params = groups.get(gender_key)

    if params is None:
        raise ValueError(f"No FastTrack config group found for gender={gender!r}")

    return {
        "min_max_formant": to_float(params.get("min_max_formant")),
        "max_max_formant": to_float(params.get("max_max_formant")),
        "max_number_of_formants": to_float(params.get("max_number_of_formants")),
        "max_plotting_frequency": to_float(params.get("max_plotting_frequency")),
        "n_formants": int(config["n_formants"]) if config.get("n_formants") is not None else None,
    }

def build_token_id(corpus: str, row: dict[str, str]) -> str:
    return ":".join(
        [
            corpus,
            row.get("speaker", ""),
            row.get("discourse", ""),
            row.get("phone", ""),
            seconds_to_ms_label(row.get("phone_begin")),
            seconds_to_ms_label(row.get("phone_end")),
        ]
    )

def get_or_create_corpus(db, corpus_name: str, config_path: Path) -> Corpus:
    corpus = db.scalar(select(Corpus).where(Corpus.name == corpus_name))
    if corpus is None:
        corpus = Corpus(name=corpus_name, config_path=str(config_path))
        db.add(corpus)
        db.flush()
    else:
        corpus.config_path = str(config_path)
    return corpus

def get_or_create_batch(db, corpus: Corpus, batch_name: str, batch_root: Path, csv_path: Path) -> Batch:
    batch = db.scalar(select(Batch).where(Batch.corpus_id == corpus.id, Batch.name == batch_name))
    if batch is None:
        batch = Batch(corpus_id=corpus.id, name=batch_name, local_root=str(batch_root), csv_path=str(csv_path))
        db.add(batch)
        db.flush()
    else:
        batch.local_root = str(batch_root)
        batch.csv_path = str(csv_path)
    return batch

def upsert_assignment(db, corpus: Corpus, batch: Batch) -> None:
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.annotator_id == ANNOTATOR_ID,
            Assignment.corpus_id == corpus.id,
            Assignment.batch_id == batch.id,
        )
    )
    if assignment is None:
        db.add(Assignment(annotator_id=ANNOTATOR_ID, corpus_id=corpus.id, batch_id=batch.id))

def find_local_file(root: Path, file_stem: str, suffix: str) -> Path | None:
    direct = root / f"{file_stem}{suffix}"
    if direct.exists():
        return direct

    matches = list(root.rglob(f"{file_stem}{suffix}"))
    return matches[0] if matches else None

def has_required_image(batch_root: Path, file_stem: str) -> bool:
    return find_local_file(batch_root / "images", file_stem, ".png") is not None

def token_values(
    row: dict[str, str],
    corpus: Corpus,
    batch: Batch,
    batch_root: Path,
    fasttrack_winners: dict[str, int],
    corpus_config: dict,
    batch_index: int,
) -> dict:
    file_stem = row["file"]
    token_id = build_token_id(corpus.name, row)
    fasttrack_params = fasttrack_params_for_gender(corpus_config, row.get("gender"))

    audio_path = find_local_file(batch_root / "audio", file_stem, ".wav")
    textgrid_path = find_local_file(batch_root / "audio", file_stem, ".TextGrid")
    image_path = find_local_file(batch_root / "images", file_stem, ".png")

    return {
        "token_id": token_id,
        "corpus_id": corpus.id,
        "batch_id": batch.id,
        "batch_index": batch_index,
        "file_stem": file_stem,
        "speaker": empty_to_none(row.get("speaker")),
        "gender": empty_to_none(row.get("gender")),
        "discourse": empty_to_none(row.get("discourse")),
        "phone": empty_to_none(row.get("phone")),
        "ipa": empty_to_none(row.get("ipa")),
        "syllable": empty_to_none(row.get("syllable")),
        "word": empty_to_none(row.get("word")),
        "transcription": empty_to_none(row.get("transcription")),
        "previous_phone": empty_to_none(row.get("previous_phone")),
        "previous_phone_ipa": empty_to_none(row.get("previous_phone_ipa")),
        "following_phone": empty_to_none(row.get("following_phone")),
        "following_phone_ipa": empty_to_none(row.get("following_phone_ipa")),
        "phone_begin": to_float(row.get("phone_begin")),
        "phone_end": to_float(row.get("phone_end")),
        "syllable_begin": to_float(row.get("syllable_begin")),
        "syllable_end": to_float(row.get("syllable_end")),
        "word_begin": to_float(row.get("word_begin")),
        "word_end": to_float(row.get("word_end")),
        "clip_begin": to_float(row.get("clip_begin")),
        "clip_end": to_float(row.get("clip_end")),
        "phone_begin_corrected": to_float(row.get("phone_begin_corrected")),
        "phone_end_corrected": to_float(row.get("phone_end_corrected")),
        "alignment": empty_to_none(row.get("alignment")),
        "alignment_comment": empty_to_none(row.get("alignment_comment")),
        "audio_path": str(audio_path) if audio_path else None,
        "textgrid_path": str(textgrid_path) if textgrid_path else None,
        "image_path": str(image_path) if image_path else None,
        "auto_winner_panel": fasttrack_winners.get(file_stem, 0),
        "min_max_formant": fasttrack_params["min_max_formant"],
        "max_max_formant": fasttrack_params["max_max_formant"],
        "n_formants": fasttrack_params["n_formants"],
        "max_number_of_formants": fasttrack_params["max_number_of_formants"],
        "max_plotting_frequency": fasttrack_params["max_plotting_frequency"],
    }

def upsert_token(db, values: dict) -> None:
    token = db.get(Token, values["token_id"])
    if token is None:
        db.add(Token(**values))
        return

    for key, value in values.items():
        setattr(token, key, value)

def synced_batch_dirs() -> list[Path]:
    if not CORPORA_DIR.exists():
        return []
    return sorted(CORPORA_DIR.glob("*/batches/*"))

def sync_one_batch(db, batch_root: Path) -> int:
    corpus_name = batch_root.parents[1].name
    batch_name = batch_root.name
    csv_path = batch_root / "batch.csv"
    fasttrack_csv_path = batch_root / "fasttrack.csv"
    config_path = batch_root.parents[1] / "config" / f"{corpus_name}.yaml"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing local batch CSV: {csv_path}")

    if not fasttrack_csv_path.exists():
        raise FileNotFoundError(f"Missing local FastTrack CSV: {fasttrack_csv_path}")

    corpus = get_or_create_corpus(db, corpus_name, config_path)
    batch = get_or_create_batch(db, corpus, batch_name, batch_root, csv_path)
    upsert_assignment(db, corpus, batch)

    fasttrack_winners = load_fasttrack_winners(fasttrack_csv_path)
    corpus_config = load_yaml(config_path)

    count = 0
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        batch_index = 0
        for row in reader:
            file_stem = empty_to_none(row.get("file"))
            if file_stem is None:
                continue

            if not has_required_image(batch_root, file_stem):
                print(f"Skipping token with missing image: {batch_root} / {file_stem}")
                continue

            upsert_token(
                db,
                token_values(
                    row,
                    corpus,
                    batch,
                    batch_root,
                    fasttrack_winners,
                    corpus_config,
                    batch_index=batch_index,
                ),
            )

            batch_index += 1
            count += 1
    
    return count

def main() -> None:
    if ANNOTATOR_ID == "unknown":
        raise RuntimeError("Set ANNOTATOR_ID in .env before syncing the database.")

    migrate_database(resolve_db_path(None))
    Base.metadata.create_all(bind=engine)

    batch_dirs = synced_batch_dirs()
    if not batch_dirs:
        print("No locally synced batches found under data/corpora/. Run scripts.sync_assigned_batches first.")
        return

    db = SessionLocal()
    try:
        total = 0
        for batch_root in batch_dirs:
            count = sync_one_batch(db, batch_root)
            total += count
            print(f"Synced database rows for {batch_root}: {count} tokens")

        db.commit()
        print(f"Database sync complete for annotator {ANNOTATOR_ID!r}: {total} tokens scanned")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()