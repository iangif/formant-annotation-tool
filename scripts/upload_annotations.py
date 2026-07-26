"""
Creates a local upload snapshot for one corpus/batch.

This file writes a lightweight SQLite snapshot here by default:

    exports/uploads/{corpus}/{batch}/annotations.sqlite

The snapshot contains:
1. metadata for tokens in requested corpus/batch
2. latest annotation per token/annotator
3. non-empty token notes
3. a small manifest table describing how the snapshot was produced

This file does not rsync to oka. Transport is done through ...
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
)
from sqlalchemy.orm import Session

from app.config import ANNOTATOR_ID, PROJECT_ROOT
from app.database import SessionLocal
from app.models import Annotation, Batch, Corpus, Token, TokenNote


SNAPSHOT_SCHEMA_VERSION = "upload_snapshot_v3"

def utcnow_iso() -> str:
    """Return a stable UTC timestamp for manifests."""

    return datetime.now(timezone.utc).isoformat()

def default_output_path(corpus: str, batch: str) -> Path:
    """Default local snapshot path."""

    return PROJECT_ROOT / "exports" / "uploads" / corpus / batch / "annotations.sqlite"

def sqlite_url(path: Path) -> str:
    """Build a SQLAlchemy SQLite URL from a filesystem path."""

    return f"sqlite:///{path.resolve()}"

def enum_value(value: Any) -> Any:
    """Convert Python Enum values into plain strings for snapshot storage."""

    if hasattr(value, "value"):
        return value.value
    return value

def iso_datetime(value: Any) -> str | None:
    """Serialize datetimes for portable SQLite snapshot storage."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)

def define_snapshot_tables(metadata: MetaData) -> dict[str, Table]:
    """Define the snapshot database tables."""
    tokens = Table(
        "tokens",
        metadata,
        __import__("sqlalchemy").Column("token_id", String, primary_key=True),
        __import__("sqlalchemy").Column("corpus", String, nullable=False),
        __import__("sqlalchemy").Column("batch", String, nullable=False),
        __import__("sqlalchemy").Column("batch_index", Integer, nullable=False),
        __import__("sqlalchemy").Column("file_stem", String, nullable=False),
        __import__("sqlalchemy").Column("speaker", String),
        __import__("sqlalchemy").Column("gender", String),
        __import__("sqlalchemy").Column("discourse", String),
        __import__("sqlalchemy").Column("phone", String),
        __import__("sqlalchemy").Column("ipa", String),
        __import__("sqlalchemy").Column("syllable", String),
        __import__("sqlalchemy").Column("word", String),
        __import__("sqlalchemy").Column("transcription", String),
        __import__("sqlalchemy").Column("previous_phone", String),
        __import__("sqlalchemy").Column("previous_phone_ipa", String),
        __import__("sqlalchemy").Column("following_phone", String),
        __import__("sqlalchemy").Column("following_phone_ipa", String),
        __import__("sqlalchemy").Column("phone_begin", Float),
        __import__("sqlalchemy").Column("phone_end", Float),
        __import__("sqlalchemy").Column("syllable_begin", Float),
        __import__("sqlalchemy").Column("syllable_end", Float),
        __import__("sqlalchemy").Column("word_begin", Float),
        __import__("sqlalchemy").Column("word_end", Float),
        __import__("sqlalchemy").Column("clip_begin", Float),
        __import__("sqlalchemy").Column("clip_end", Float),
        __import__("sqlalchemy").Column("phone_begin_corrected", Float),
        __import__("sqlalchemy").Column("phone_end_corrected", Float),
        __import__("sqlalchemy").Column("alignment", String),
        __import__("sqlalchemy").Column("alignment_comment", Text),
        __import__("sqlalchemy").Column("auto_winner_panel", Integer),
        __import__("sqlalchemy").Column("n_candidates", Integer),
        __import__("sqlalchemy").Column("max_plotting_frequency", Float),
        __import__("sqlalchemy").Column("candidates_pickle_path", String),
    )

    annotations = Table(
        "annotations",
        metadata,
        __import__("sqlalchemy").Column("annotation_id", Integer, primary_key=True),
        __import__("sqlalchemy").Column("token_id", String, nullable=False, index=True),
        __import__("sqlalchemy").Column("annotator_id", String, nullable=False, index=True),
        __import__("sqlalchemy").Column("decision", String, nullable=False),
        __import__("sqlalchemy").Column("selected_panel", Integer),
        __import__("sqlalchemy").Column("panel_f1", Integer),
        __import__("sqlalchemy").Column("panel_f2", Integer),
        __import__("sqlalchemy").Column("panel_f3", Integer),
        __import__("sqlalchemy").Column("panel_f4", Integer),
        __import__("sqlalchemy").Column("needs_correction_f1", Boolean, nullable=False),
        __import__("sqlalchemy").Column("needs_correction_f2", Boolean, nullable=False),
        __import__("sqlalchemy").Column("needs_correction_f3", Boolean, nullable=False),
        __import__("sqlalchemy").Column("needs_correction_f4", Boolean, nullable=False),
        __import__("sqlalchemy").Column("annotation_version", String),
        __import__("sqlalchemy").Column("created_at", String),
    )

    token_notes = Table(
        "token_notes",
        metadata,
        __import__("sqlalchemy").Column("note_id", Integer, primary_key=True),
        __import__("sqlalchemy").Column("token_id", String, nullable=False, index=True),
        __import__("sqlalchemy").Column("annotator_id", String, nullable=False, index=True),
        __import__("sqlalchemy").Column("note", Text, nullable=False),
        __import__("sqlalchemy").Column("created_at", String),
        __import__("sqlalchemy").Column("updated_at", String),
    )

    manifest = Table(
        "manifest",
        metadata,
        __import__("sqlalchemy").Column("key", String, primary_key=True),
        __import__("sqlalchemy").Column("value", Text, nullable=False),
    )

    return {
        "tokens": tokens,
        "annotations": annotations,
        "token_notes": token_notes,
        "manifest": manifest,
    }

def get_batch_or_raise(db: Session, corpus_name: str, batch_name: str) -> Batch:
    """Return the requested batch, or raise a clear error."""

    stmt = (
        select(Batch)
        .join(Corpus, Corpus.id == Batch.corpus_id)
        .where(Corpus.name == corpus_name)
        .where(Batch.name == batch_name)
        .limit(1)
    )

    batch = db.scalar(stmt)

    if batch is None:
        raise RuntimeError(
            f"No local batch found for corpus={corpus_name!r}, batch={batch_name!r}. "
            "Run scripts/sync_assigned_batches.py and scripts/sync_database.py first."
        )

    return batch

def load_tokens_for_batch(db: Session, batch: Batch) -> list[Token]:
    """Load all tokens in stable batch display order."""

    stmt = (
        select(Token)
        .where(Token.batch_id == batch.id)
        .order_by(Token.batch_index.asc(), Token.token_id.asc())
    )

    return list(db.scalars(stmt))

def latest_annotations_for_batch(
    db: Session,
    batch: Batch,
    annotator_id: str | None,
) -> list[Annotation]:
    """
    Return latest annotations for tokens in a batch.

    If annotator_id is provided, only that annotator's latest annotation per
    token is included.

    If annotator_id is None, the latest annotation per (token, annotator) pair
    is included. That is useful for local testing with multi-annotator DBs.
    """

    row_number = func.row_number().over(
        partition_by=(
            (Annotation.token_id, Annotation.annotator_id)
            if annotator_id is None
            else Annotation.token_id
        ),
        order_by=(Annotation.created_at.desc(), Annotation.id.desc()),
    )

    ranked = (
        select(
            Annotation.id.label("annotation_id"),
            row_number.label("rn"),
        )
        .join(Token, Token.token_id == Annotation.token_id)
        .where(Token.batch_id == batch.id)
    )

    if annotator_id is not None:
        ranked = ranked.where(Annotation.annotator_id == annotator_id)

    ranked_subquery = ranked.subquery()

    stmt = (
        select(Annotation)
        .join(ranked_subquery, ranked_subquery.c.annotation_id == Annotation.id)
        .where(ranked_subquery.c.rn == 1)
        .order_by(Annotation.token_id.asc(), Annotation.annotator_id.asc())
    )

    return list(db.scalars(stmt))

def token_notes_for_batch(
    db: Session,
    batch: Batch,
    annotator_id: str | None,
) -> list[TokenNote]:
    """Load non-empty token notes for tokens in a batch."""

    stmt = (
        select(TokenNote)
        .join(Token, Token.token_id == TokenNote.token_id)
        .where(Token.batch_id == batch.id)
        .where(func.trim(TokenNote.note) != "")
    )

    if annotator_id is not None:
        stmt = stmt.where(TokenNote.annotator_id == annotator_id)

    return list(db.scalars(stmt))

def token_to_row(token: Token, corpus_name: str, batch_name: str) -> dict[str, Any]:
    """Convert an app Token ORM object into a snapshot row."""

    return {
        "token_id": token.token_id,
        "corpus": corpus_name,
        "batch": batch_name,
        "batch_index": token.batch_index,
        "file_stem": token.file_stem,
        "speaker": token.speaker,
        "gender": token.gender,
        "discourse": token.discourse,
        "phone": token.phone,
        "ipa": token.ipa,
        "syllable": token.syllable,
        "word": token.word,
        "transcription": token.transcription,
        "previous_phone": token.previous_phone,
        "previous_phone_ipa": token.previous_phone_ipa,
        "following_phone": token.following_phone,
        "following_phone_ipa": token.following_phone_ipa,
        "phone_begin": token.phone_begin,
        "phone_end": token.phone_end,
        "syllable_begin": token.syllable_begin,
        "syllable_end": token.syllable_end,
        "word_begin": token.word_begin,
        "word_end": token.word_end,
        "clip_begin": token.clip_begin,
        "clip_end": token.clip_end,
        "phone_begin_corrected": token.phone_begin_corrected,
        "phone_end_corrected": token.phone_end_corrected,
        "alignment": token.alignment,
        "alignment_comment": token.alignment_comment,
        "auto_winner_panel": token.auto_winner_panel,
        "n_candidates": token.n_candidates,
        "max_plotting_frequency": token.max_plotting_frequency,
        "candidates_pickle_path": token.candidates_pickle_path,
    }

def annotation_to_row(annotation: Annotation) -> dict[str, Any]:
    """Convert an app Annotation ORM object into a snapshot row."""

    return {
        "annotation_id": annotation.id,
        "token_id": annotation.token_id,
        "annotator_id": annotation.annotator_id,
        "decision": enum_value(annotation.decision),
        "selected_panel": annotation.selected_panel,
        "panel_f1": annotation.panel_f1,
        "panel_f2": annotation.panel_f2,
        "panel_f3": annotation.panel_f3,
        "panel_f4": annotation.panel_f4,
        "needs_correction_f1": annotation.needs_correction_f1,
        "needs_correction_f2": annotation.needs_correction_f2,
        "needs_correction_f3": annotation.needs_correction_f3,
        "needs_correction_f4": annotation.needs_correction_f4,
        "annotation_version": annotation.annotation_version,
        "created_at": iso_datetime(annotation.created_at),
    }

def token_note_to_row(note: TokenNote) -> dict[str, Any]:
    return {
        "note_id": note.id,
        "token_id": note.token_id,
        "annotator_id": note.annotator_id,
        "note": note.note,
        "created_at": iso_datetime(note.created_at),
        "updated_at": iso_datetime(note.updated_at),
    }

def write_snapshot(
    *,
    output_path: Path,
    corpus_name: str,
    batch_name: str,
    annotator_id: str | None,
    tokens: list[Token],
    annotations: list[Annotation],
    token_notes: list[TokenNote],
) -> None:
    """Create the output SQLite snapshot from token and annotation rows."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        output_path.unlink()

    engine = create_engine(sqlite_url(output_path))
    metadata = MetaData()
    tables = define_snapshot_tables(metadata)
    metadata.create_all(engine)

    token_rows = [
        token_to_row(token, corpus_name=corpus_name, batch_name=batch_name)
        for token in tokens
    ]
    annotation_rows = [annotation_to_row(annotation) for annotation in annotations]
    token_note_rows = [token_note_to_row(note) for note in token_notes]

    manifest_rows = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "created_at": utcnow_iso(),
        "corpus": corpus_name,
        "batch": batch_name,
        "annotator_id": annotator_id or "ALL",
        "token_count": str(len(token_rows)),
        "latest_annotation_count": str(len(annotation_rows)),
        "token_note_count": str(len(token_note_rows)),
        "contains_annotation_history": "false",
        "source": "formant-annotation-tool scripts/upload_annotations.py",
    }

    with engine.begin() as conn:
        if token_rows:
            conn.execute(insert(tables["tokens"]), token_rows)

        if annotation_rows:
            conn.execute(insert(tables["annotations"]), annotation_rows)

        if token_note_rows:
            conn.execute(insert(tables["token_notes"]), token_note_rows)

        conn.execute(
            insert(tables["manifest"]),
            [{"key": key, "value": value} for key, value in manifest_rows.items()],
        )

    # A JSON sidecar makes quick inspection easy without opening SQLite.
    manifest_json_path = output_path.with_suffix(".manifest.json")
    manifest_json_path.write_text(
        json.dumps(manifest_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local upload snapshot for one corpus/batch."
    )

    parser.add_argument("corpus", help="Corpus name, e.g. ls_eng")
    parser.add_argument("batch", help="Batch name, e.g. batch1")

    parser.add_argument(
        "--annotator-id",
        default=ANNOTATOR_ID,
        help=(
            "Annotator ID to export. Defaults to ANNOTATOR_ID from .env. "
            "Ignored when --all-annotators is used."
        ),
    )

    parser.add_argument(
        "--all-annotators",
        action="store_true",
        help=(
            "Include the latest annotation per token per annotator. "
            "Useful for local testing with a multi-annotator database."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output SQLite path. Defaults to "
            "exports/uploads/{corpus}/{batch}/annotations.sqlite"
        ),
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    output_path = args.output or default_output_path(args.corpus, args.batch)
    annotator_id = None if args.all_annotators else args.annotator_id

    if not annotator_id and not args.all_annotators:
        raise RuntimeError(
            "No annotator ID was provided. Set ANNOTATOR_ID in .env or pass --annotator-id."
        )

    with SessionLocal() as db:
        batch = get_batch_or_raise(db, args.corpus, args.batch)
        tokens = load_tokens_for_batch(db, batch)
        annotations = latest_annotations_for_batch(
            db=db,
            batch=batch,
            annotator_id=annotator_id,
        )
        token_notes = token_notes_for_batch(
            db=db,
            batch=batch,
            annotator_id=annotator_id,
        )

    write_snapshot(
        output_path=output_path,
        corpus_name=args.corpus,
        batch_name=args.batch,
        annotator_id=annotator_id,
        tokens=tokens,
        annotations=annotations,
        token_notes=token_notes,
    )

    print(f"Created upload snapshot: {output_path}")
    print(f"Tokens included: {len(tokens)}")
    print(f"Latest annotations included: {len(annotations)}")
    print(f"Token notes included: {len(token_notes)}")


if __name__ == "__main__":
    main()
