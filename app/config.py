"""
Application configuration.

Reads values from environment variables (.env)
"""

import os
from dotenv import load_dotenv

load_dotenv()

ANNOTATOR_ID = os.getenv("ANNOTATOR_ID", "unknown")