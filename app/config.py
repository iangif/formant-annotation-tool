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

ANNOTATOR_ID = os.getenv("ANNOTATOR_ID", "unknown")

FORMANT_DB_URL = os.getenv(
    "FORMANT_DB_URL",
    f"sqlite:///./data/{ANNOTATOR_ID}.sqlite",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STATIC_DIR = PROJECT_ROOT / "app" / "static"
TEMPLATES_DIR = PROJECT_ROOT / "app" / "templates"