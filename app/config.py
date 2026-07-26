"""
Application configuration.

This module centralizes environment settings.

Each annotator has their own .env file:

    ANNOTATOR_ID=ian
    FORMANT_DB_URL=sqlite:///./data/ian.sqlite

If FORMANT_DB_URL is not provided, use default:

    sqlite:///./data/{ANNOTATOR_ID}.sqlite
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CORPORA_DIR = DATA_DIR / "corpora"
SYNC_MANIFEST_PATH = DATA_DIR / "sync_manifest.json"

ANNOTATOR_ID = os.getenv("ANNOTATOR_ID", "unknown")

FORMANT_DB_URL = os.getenv(
    "FORMANT_DB_URL",
    f"sqlite:///./data/{ANNOTATOR_ID}.sqlite",
)

REMOTE_USER_HOST = os.getenv("REMOTE_USER_HOST", "")
REMOTE_PROJECT_ROOT = Path(os.getenv("REMOTE_PROJECT_ROOT", "/projects/xling-measures"))
REMOTE_CONFIG_DIR = f"{REMOTE_PROJECT_ROOT}/formants/config"

ADJUDICATION_CENTRAL_DB_PATH = Path(
    str(REMOTE_PROJECT_ROOT / "export" / "central_annotations.sqlite")
)
ADJUDICATION_MEDIA_ROOT = Path(
    str(REMOTE_PROJECT_ROOT / "data")
)

PRAAT_PATH = os.getenv("PRAAT_PATH") or None

STATIC_DIR = PROJECT_ROOT / "app" / "static"
TEMPLATES_DIR = PROJECT_ROOT / "app" / "templates"
