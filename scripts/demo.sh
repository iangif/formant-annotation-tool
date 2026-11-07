#!/usr/bin/env bash
# Public demo: runs the annotation app on the bundled demo corpus.

set -e

uv sync --frozen --no-install-package formants-export

export ANNOTATOR_ID="${ANNOTATOR_ID:-demo}"

uv run --no-sync python -m scripts.migrate_needs_correction_flags
uv run --no-sync python -m scripts.migrate_token_rendering_metadata
uv run --no-sync python -m scripts.sync_database --corpus demo

echo ""
echo "Formant Annotation Tool demo: open http://127.0.0.1:8000 and press Demo"
echo ""
uv run --no-sync fastapi run app/main.py --host 127.0.0.1 --port 8000
