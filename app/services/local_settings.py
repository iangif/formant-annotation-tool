"""
Small local settings store.

Used for local-only UI preferences such as the last opened batch.
TODO: writes settings to database.
"""

import json
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

SETTINGS_PATH = DATA_DIR / "local_settings.json"

def _read_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}

    with SETTINGS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

def _write_settings(settings: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2, sort_keys=True)

def get_last_opened_batch_id(annotator_id: str) -> int | None:
    value = _read_settings().get("last_opened_batch_by_annotator", {}).get(annotator_id)
    return int(value) if value is not None else None

def set_last_opened_batch_id(annotator_id: str, batch_id: int) -> None:
    settings = _read_settings()
    settings.setdefault("last_opened_batch_by_annotator", {})[annotator_id] = batch_id
    _write_settings(settings)