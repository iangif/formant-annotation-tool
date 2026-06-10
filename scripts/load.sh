#!/usr/bin/env bash

set -e

if [ $# -ne 1 ]; then
    echo "Usage:"
    echo "  ./scripts/load.sh <corpus>"
    echo
    echo "Example:"
    echo "  ./scripts/load.sh ls_eng"
    exit 1
fi

CORPUS="$1"

echo
echo "=== Syncing assigned batches for ${CORPUS} ==="
uv run python -m scripts.sync_assigned_batches --corpus "$CORPUS"

echo
echo "=== Updating local database ==="
uv run python -m scripts.sync_database

echo
echo "Load complete."