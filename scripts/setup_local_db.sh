#!/usr/bin/env bash

set -e

echo "Setting up local Formant Annotation Tool database..."

echo "Initializing database..."
uv run python -m scripts.init_db

echo "Importing tokens..."
uv run python -m scripts.import_tokens

echo "Importing assignments..."
uv run python -m scripts.import_assignments

echo ""
echo "Setup complete."