#!/usr/bin/env bash

set -e

echo "Starting Formant Annotation Tool..."
echo "Open this URL in your browser:"
echo "  http://127.0.0.1:8000"
echo ""

uv run python -m scripts.migrate_needs_correction_flags
uv run python -m scripts.migrate_token_rendering_metadata
uv run fastapi run app/main.py --host 127.0.0.1 --port 8000
