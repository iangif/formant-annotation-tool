"""
One-time cleanup for local annotator databases.

Removes tokens whose required image is missing, deletes their annotations, and reindexes the remaining tokens within each batch.

Run from project root:

    uv run python -m scripts.cleanup_missing_image_tokens

After run:

    ./scripts/load.sh ls_eng
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import delete, select

from app.config import ANNOTATOR_ID, CORPORA_DIR
from app.database import Base, SessionLocal, engine
from app.models import Annotation, Batch, Corpus, Token
from scripts.sync_database import build_token_id, find_local_file

def synced_batch_dirs() -> list[Path]:
    if not CORPORA_DIR.exists():
        return []

    return sorted(CORPORA_DIR.glob("*/batches/*"))

def valid_tokens_for_batch(batch_root: Path, corpus_name: str) -> dict[str, int]:
    """
    Return {token_id: new_batch_index} for rows in batch.csv that have a PNG.
    """
    csv_path = batch_root / "batch.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing local batch CSV: {csv_path}")

    valid: dict[str, int] = {}
    next_index = 0

    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            file_stem = row.get("file")
            if not file_stem:
                continue

            image_path = find_local_file(batch_root / "images", file_stem, ".png")
            if image_path is None:
                continue

            token_id = build_token_id(corpus_name, row)
            valid[token_id] = next_index
            next_index += 1

    return valid

def cleanup_one_batch(db, batch_root: Path) -> tuple[int, int]:
    corpus_name = batch_root.parents[1].name
    batch_name = batch_root.name

    corpus = db.scalar(select(Corpus).where(Corpus.name == corpus_name))
    if corpus is None:
        print(f"Skipping {corpus_name}/{batch_name}: corpus not in database")
        return 0, 0

    batch = db.scalar(
        select(Batch).where(
            Batch.corpus_id == corpus.id,
            Batch.name == batch_name,
        )
    )
    if batch is None:
        print(f"Skipping {corpus_name}/{batch_name}: batch not in database")
        return 0, 0

    valid_indices = valid_tokens_for_batch(batch_root, corpus_name)
    valid_token_ids = set(valid_indices)

    # Reindex valid tokens.
    reindexed = 0
    for token_id, new_index in valid_indices.items():
        token = db.get(Token, token_id)
        if token is not None and token.batch_index != new_index:
            token.batch_index = new_index
            reindexed += 1

    # Delete invalid tokens already present in this batch.
    invalid_tokens = db.scalars(
        select(Token).where(Token.batch_id == batch.id)
    ).all()

    deleted = 0
    for token in invalid_tokens:
        if token.token_id in valid_token_ids:
            continue

        db.execute(delete(Annotation).where(Annotation.token_id == token.token_id))
        db.delete(token)
        deleted += 1

    return deleted, reindexed

def main() -> None:
    if ANNOTATOR_ID == "unknown":
        raise RuntimeError("Set ANNOTATOR_ID in .env before running cleanup.")

    Base.metadata.create_all(bind=engine)

    batch_dirs = synced_batch_dirs()
    if not batch_dirs:
        print("No locally synced batches found under data/corpora/.")
        return

    db = SessionLocal()
    try:
        total_deleted = 0
        total_reindexed = 0

        for batch_root in batch_dirs:
            deleted, reindexed = cleanup_one_batch(db, batch_root)
            total_deleted += deleted
            total_reindexed += reindexed

            print(
                f"Cleaned {batch_root}: "
                f"{deleted} missing-image tokens removed, "
                f"{reindexed} kept tokens reindexed"
            )

        db.commit()

        print()
        print(
            f"Cleanup complete for annotator {ANNOTATOR_ID!r}: "
            f"{total_deleted} tokens removed, "
            f"{total_reindexed} tokens reindexed"
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()