"""Add rendering metadata columns to an existing local annotation database.

SQLAlchemy's ``create_all`` does not alter existing tables. This idempotent
migration lets established annotator databases receive new token metadata
without being rebuilt or losing annotations.

Run directly when needed:

    uv run python -m scripts.migrate_token_rendering_metadata
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
    """Resolve a direct path or the configured local SQLite URL."""

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


def migrate_database(db_path: Path) -> int:
    """Add ``max_plotting_frequency`` if the tokens table already exists."""

    if not db_path.exists():
        return 0

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'tokens'"
        ).fetchone()
        if table_exists is None:
            return 0

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(tokens)")
        }
        if "max_plotting_frequency" in columns:
            return 0

        with connection:
            connection.execute(
                "ALTER TABLE tokens ADD COLUMN max_plotting_frequency FLOAT"
            )
        return 1
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add stored token rendering metadata to a local SQLite database."
    )
    parser.add_argument(
        "--db",
        help="Path to the local SQLite database. Defaults to FORMANT_DB_URL.",
    )
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    added = migrate_database(db_path)
    if db_path.exists():
        print(
            "Token rendering metadata migration complete: "
            f"added {added} column(s)."
        )


if __name__ == "__main__":
    main()
