#!/usr/bin/env bash
set -euo pipefail

# Full annotator upload workflow.
#
# Usage:
#   ./scripts/upload.sh ls_eng batch1
#
# This:
#   1. creates exports/uploads/<corpus>/<batch>/annotations.sqlite
#   2. rsyncs it to oka
#   3. deletes the local upload snapshot after successful rsync

if [ "$#" -lt 2 ]; then
  echo "Usage: ./scripts/upload.sh <corpus> <batch>"
  echo "Example: ./scripts/upload.sh ls_eng batch1"
  exit 1
fi

CORPUS="$1"
BATCH="$2"

uv run python -m scripts.migrate_needs_correction_flags
uv run python -m scripts.migrate_token_rendering_metadata
uv run python -m scripts.upload_annotations "$CORPUS" "$BATCH"
uv run python -m scripts.rsync_upload "$CORPUS" "$BATCH"
