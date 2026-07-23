"""Migrate token-level ``needs_correction`` decisions to per-formant flags.

The migration is idempotent and runs automatically from ``start_app.sh`` and
``upload.sh``. It can also be run directly:

    uv run python -m scripts.migrate_needs_correction_flags

Legacy rows retain their closest selected panels. If all four legacy panel
fields are blank, all four are filled with the token's auto-winner panel. Since
the old decision did not identify a particular formant, all four new correction
flags are conservatively set to true.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORRECTION_COLUMNS = [f"needs_correction_f{index}" for index in range(1, 5)]
PANEL_COLUMNS = [f"panel_f{index}" for index in range(1, 5)]


def resolve_db_path(db_arg: str | None) -> Path:
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

    raw_path = unquote(urlparse(db_url).path)
    if raw_path.startswith("/./"):
        raw_path = raw_path[3:]
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}


def add_flag_columns(conn: sqlite3.Connection) -> int:
    existing = table_columns(conn, "annotations")
    added = 0
    for column in CORRECTION_COLUMNS:
        if column not in existing:
            conn.execute(
                f"ALTER TABLE annotations ADD COLUMN {column} "
                "BOOLEAN NOT NULL DEFAULT 0"
            )
            added += 1
    return added


def derive_decision(panels: list[int | None], auto_winner: int) -> tuple[str, int | None]:
    if all(panel is not None for panel in panels) and len(set(panels)) == 1:
        selected = panels[0]
        return (
            ("accept_auto" if selected == auto_winner else "select_panel"),
            selected,
        )
    return "complex", None


def migrate_legacy_rows(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT
            a.id,
            a.panel_f1,
            a.panel_f2,
            a.panel_f3,
            a.panel_f4,
            t.auto_winner_panel
        FROM annotations AS a
        JOIN tokens AS t ON t.token_id = a.token_id
        WHERE a.decision = 'needs_correction'
        ORDER BY a.id
        """
    ).fetchall()

    for row in rows:
        panels = [row[column] for column in PANEL_COLUMNS]
        if all(panel is None for panel in panels):
            winner = row["auto_winner_panel"]
            if winner is None:
                raise RuntimeError(
                    f"Legacy annotation {row['id']} has no panels and its token "
                    "has no auto_winner_panel."
                )
            panels = [int(winner)] * 4

        decision, selected_panel = derive_decision(
            panels,
            int(row["auto_winner_panel"]),
        )
        conn.execute(
            """
            UPDATE annotations
            SET
                decision = ?,
                selected_panel = ?,
                panel_f1 = ?,
                panel_f2 = ?,
                panel_f3 = ?,
                panel_f4 = ?,
                needs_correction_f1 = 1,
                needs_correction_f2 = 1,
                needs_correction_f3 = 1,
                needs_correction_f4 = 1,
                annotation_version = 'v2_migrated'
            WHERE id = ?
            """,
            (decision, selected_panel, *panels, row["id"]),
        )
    return len(rows)


def migrate_database(db_path: Path) -> tuple[int, int]:
    if not db_path.exists():
        return 0, 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "annotations"):
            return 0, 0
        with conn:
            added = add_flag_columns(conn)
            migrated = migrate_legacy_rows(conn)
        return added, migrated
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate needs_correction decisions to per-formant flags."
    )
    parser.add_argument(
        "--db",
        help="Path to the local SQLite database. Defaults to FORMANT_DB_URL.",
    )
    args = parser.parse_args()
    db_path = resolve_db_path(args.db)
    added, migrated = migrate_database(db_path)
    if db_path.exists():
        print(
            f"Needs-correction migration complete: added {added} column(s), "
            f"migrated {migrated} legacy annotation(s)."
        )


if __name__ == "__main__":
    main()
