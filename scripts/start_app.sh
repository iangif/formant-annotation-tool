#!/usr/bin/env bash

set -e

echo "Starting Formant Annotation Tool..."
echo "Open this URL in your browser:"
echo "  https://127.0.0.1:8000"
echo ""

uv run fastapi run app/main.py