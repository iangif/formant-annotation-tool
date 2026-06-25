"""
Rsync a locally created upload snapshot to oka.

Expected workflow:

    uv run python -m scripts.upload_annotations ls_eng batch1
    uv run python -m scripts.rsync_upload ls_eng batch1

After a successful rsync, the local snapshot directory is deleted.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from app.config import ANNOTATOR_ID, PROJECT_ROOT, REMOTE_USER_HOST


REMOTE_UPLOAD_ROOT = "/projects/xling-measures/export/annotation_uploads"

def local_snapshot_path(corpus: str, batch: str) -> Path:
    return PROJECT_ROOT / "exports" / "uploads" / corpus / batch / "annotations.sqlite"

def local_snapshot_dir(corpus: str, batch: str) -> Path:
    return PROJECT_ROOT / "exports" / "uploads" / corpus / batch

def remote_snapshot_dir(annotator_id: str, corpus: str, batch: str) -> str:
    return f"{REMOTE_UPLOAD_ROOT}/{annotator_id}/{corpus}/{batch}"

def run_command(command: list[str]) -> None:
    """Run a shell command safely and raise a readable error on failure."""

    result = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"{' '.join(command)}\n\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}"
        )

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rsync a local annotation upload snapshot to oka."
    )

    parser.add_argument("corpus", help="Corpus name, e.g. ls_eng")
    parser.add_argument("batch", help="Batch name, e.g. batch1")

    parser.add_argument(
        "--annotator-id",
        default=ANNOTATOR_ID,
        help="Annotator ID. Defaults to ANNOTATOR_ID from .env.",
    )

    parser.add_argument(
        "--keep-local",
        action="store_true",
        help="Do not delete the local upload snapshot after successful rsync.",
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    if not REMOTE_USER_HOST:
        raise RuntimeError(
            "REMOTE_USER_HOST is not set. Add it to .env, for example:\n"
            "REMOTE_USER_HOST=username@oka"
        )

    if not args.annotator_id:
        raise RuntimeError(
            "No annotator ID found. Set ANNOTATOR_ID in .env or pass --annotator-id."
        )

    snapshot = local_snapshot_path(args.corpus, args.batch)
    snapshot_dir = local_snapshot_dir(args.corpus, args.batch)
    remote_dir = remote_snapshot_dir(args.annotator_id, args.corpus, args.batch)

    if not snapshot.exists():
        raise RuntimeError(
            f"Local upload snapshot does not exist:\n{snapshot}\n\n"
            "Run scripts/upload_annotations.py first."
        )

    # Ensure the remote destination directory exists.
    run_command(["ssh", REMOTE_USER_HOST, "mkdir", "-p", remote_dir])

    # Copy the SQLite snapshot and manifest sidecar if present.
    files_to_upload = [snapshot]

    manifest = snapshot.with_suffix(".manifest.json")
    if manifest.exists():
        files_to_upload.append(manifest)

    run_command(
        [
            "rsync",
            "-av",
            *[str(path) for path in files_to_upload],
            f"{REMOTE_USER_HOST}:{remote_dir}/",
        ]
    )

    if not args.keep_local:
        shutil.rmtree(snapshot_dir)

    print(f"Uploaded snapshot to: {REMOTE_USER_HOST}:{remote_dir}/")
    if args.keep_local:
        print(f"Kept local snapshot at: {snapshot_dir}")
    else:
        print(f"Deleted local snapshot directory: {snapshot_dir}")


if __name__ == "__main__":
    main()