"""
Migrate legacy annotation notes into the new mutable token_notes table.

Run from the project root:

    uv run python -m scripts.migrate_annotation_notes_to_token_notes

Optional, only after app code no longer uses annotations.notes:

    uv run python -m scripts.migrate_annotation_notes_to_token_notes --drop-old-column

Default behavior is conservative:
- copies only notes from the latest annotation per token/annotator
- does not overwrite existing token_notes rows
- does not drop annotations.notes unless explicitly requested
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_db_path(db_arg: str | None) -> Path:
    """Resolve the SQLite DB path from --db or FORMANT_DB_URL."""

    load_dotenv(PROJECT_ROOT / ".env")

    if db_arg:
        return Path(db_arg).expanduser().resolve()

    annotator_id = os.getenv("ANNOTATOR_ID", "unknown")
    db_url = os.getenv("FORMANT_DB_URL", f"sqlite:///./data/{annotator_id}.sqlite")

    if not db_url.startswith("sqlite:///"):
        raise ValueError(
            "This migration only supports local SQLite databases. "
            f"Got FORMANT_DB_URL={db_url!r}"
        )

    parsed = urlparse(db_url)
    raw_path = unquote(parsed.path)

    # sqlite:///./data/foo.sqlite is parsed as path="/./data/foo.sqlite".
    if raw_path.startswith("/./"):
        raw_path = raw_path[3:]

    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def require_token_notes_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "token_notes"):
        raise RuntimeError(
            "token_notes table does not exist.\n\n"
            "Run ./scripts/load.sh before running this migration."
        )


def migrate_latest_annotation_notes(
    conn: sqlite3.Connection,
    *,
    overwrite_existing: bool,
) -> int:
    """
    Copy notes from each latest annotation into token_notes.

    Latest annotation is determined per (token_id, annotator_id), ordered by:
        created_at DESC, id DESC

    Empty/whitespace-only notes are ignored.
    """

    if not table_exists(conn, "annotations"):
        raise RuntimeError("Missing annotations table.")

    if not column_exists(conn, "annotations", "notes"):
        print("annotations.notes does not exist; nothing to copy.")
        return 0

    latest_notes = conn.execute(
        """
        SELECT
            a.token_id,
            a.annotator_id,
            a.notes,
            COALESCE(a.created_at, CURRENT_TIMESTAMP) AS note_time
        FROM annotations AS a
        WHERE a.id = (
            SELECT a2.id
            FROM annotations AS a2
            WHERE
                a2.token_id = a.token_id
                AND a2.annotator_id = a.annotator_id
            ORDER BY a2.created_at DESC, a2.id DESC
            LIMIT 1
        )
        AND a.notes IS NOT NULL
        AND TRIM(a.notes) != ''
        """
    ).fetchall()

    migrated = 0

    for row in latest_notes:
        if overwrite_existing:
            conn.execute(
                """
                INSERT INTO token_notes (
                    token_id,
                    annotator_id,
                    note,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(token_id, annotator_id)
                DO UPDATE SET
                    note = excluded.note,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    row["token_id"],
                    row["annotator_id"],
                    row["notes"],
                    row["note_time"],
                ),
            )
            migrated += 1
        else:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO token_notes (
                    token_id,
                    annotator_id,
                    note,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    row["token_id"],
                    row["annotator_id"],
                    row["notes"],
                    row["note_time"],
                ),
            )
            migrated += cursor.rowcount

    return migrated


def drop_annotations_notes_column(conn: sqlite3.Connection) -> None:
    """
    Drop the legacy annotations.notes column.

    This requires SQLite 3.35+. Do this only after the app no longer maps or
    reads Annotation.notes.
    """

    if not column_exists(conn, "annotations", "notes"):
        print("annotations.notes is already absent.")
        return

    conn.execute("ALTER TABLE annotations DROP COLUMN notes")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate legacy annotation notes into token_notes."
    )
    parser.add_argument(
        "--db",
        help="Path to the local SQLite database. Defaults to FORMANT_DB_URL.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Overwrite existing token_notes rows with migrated annotation notes.",
    )
    parser.add_argument(
        "--drop-old-column",
        action="store_true",
        help="Drop annotations.notes after migration. Only use after app code is updated.",
    )
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    print(f"Migrating notes in: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        with conn:
            require_token_notes_table(conn)
            migrated = migrate_latest_annotation_notes(
                conn,
                overwrite_existing=args.overwrite_existing,
            )

            if args.drop_old_column:
                drop_annotations_notes_column(conn)

        print(f"Done. Migrated {migrated} note(s) into token_notes.")

        if not args.drop_old_column:
            print(
                "Left annotations.notes in place. "
                "Drop it later with --drop-old-column after the app no longer uses it."
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()