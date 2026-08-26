"""
Sync only the batches assigned to the current annotator.
Accesses batches on oka over SSH/rsync.

Run from the project root:
    uv run python -m scripts.sync_assigned_batches --corpus ls_eng
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import ANNOTATOR_ID, CORPORA_DIR, REMOTE_USER_HOST, SYNC_MANIFEST_PATH, REMOTE_CONFIG_DIR

@dataclass(frozen=True)
class AssignedBatch:
    corpus: str
    batch: str

def run_rsync(remote_source: str, local_dest: Path, extra_args: list[str] | None = None) -> None:
    if not REMOTE_USER_HOST:
        raise SystemExit(
            "\nError: REMOTE_USER_HOST is not set.\n"
            "Set it in .env, for example:\n"
            "  REMOTE_USER_HOST=username@oka\n"
        )

    local_dest.mkdir(parents=True, exist_ok=True)

    command = [
        "rsync",
        "-a",
        "--update", # Skips files that are already at destination with more recent modification time
        # "--delete", # destroys files at the destination if they do longer exist in the source (true data mirroring)
        "--info=progress2",
    ]

    if extra_args:
        command.extend(extra_args)

    command.extend(
        [
            f"{REMOTE_USER_HOST}:{remote_source}",
            str(local_dest),
        ]
    )

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SystemExit("\nError: rsync is not installed or is not available on PATH.\n") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"\nError: rsync failed while copying from Oka.\n"
            f"Remote source: {remote_source}\n"
            f"Local destination: {local_dest}\n"
            f"rsync exited with status {exc.returncode}.\n"
            "See the rsync output above for details.\n"
        ) from exc

def rsync_file(remote_file: str, local_dir: Path) -> None:
    run_rsync(remote_file, local_dir)

def rsync_filtered_dir(remote_dir: str, local_dir: Path, include_patterns: list[str]) -> None:
    extra_args = []

    for pattern in include_patterns:
        extra_args.extend(["--include", pattern])

    extra_args.extend(["--exclude", "*"])

    # Trailing slash copies directory contents into local_dir
    run_rsync(f"{remote_dir.rstrip('/')}/", local_dir, extra_args=extra_args)

def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing local YAML file: {path}")

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def load_manifest() -> dict[str, Any]:
    if not SYNC_MANIFEST_PATH.exists():
        return {"batches": {}}

    with SYNC_MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_manifest(manifest: dict[str, Any]) -> None:
    SYNC_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    with SYNC_MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, sort_keys=True)
        file.write("\n")

def sync_corpus_config(corpus: str) -> Path:
    local_config_dir = CORPORA_DIR / corpus / "config"
    remote_config_path = f"{REMOTE_CONFIG_DIR}/{corpus}.yaml"

    rsync_file(remote_config_path, local_config_dir)

    return local_config_dir / f"{corpus}.yaml"

def assigned_batches_from_corpus_config(corpus: str, config: dict[str, Any], annotator_id: str) -> list[AssignedBatch]:
    batch_names = (config.get("batches") or {}).keys()

    assigned: list[AssignedBatch] = []
    for batch_name in batch_names:
        raw_annotators = config.get(batch_name)

        if raw_annotators is None:
            annotators: list[str] = []
        elif isinstance(raw_annotators, list):
            annotators = [str(value) for value in raw_annotators]
        else:
            raise ValueError(
                f"Expected batch assignment for {batch_name!r} to be a list or empty, "
                f"but got {type(raw_annotators).__name__}."
            )

        if annotator_id in annotators:
            assigned.append(AssignedBatch(corpus=corpus, batch=str(batch_name)))

    return assigned

def sync_batch(item: AssignedBatch, config: dict[str, Any]) -> dict[str, Any] | None:
    output_root = config["output_root"]
    csv_output_dir = config["csv_output_dir"]

    local_corpus_root = CORPORA_DIR / item.corpus
    local_batch_root = local_corpus_root / "batches" / item.batch
    local_csv_dir = local_batch_root
    local_audio_dir = local_batch_root / "audio"
    local_images_dir = local_batch_root / "images"

    remote_csv = f"{csv_output_dir.rstrip('/')}/{item.batch}.csv"
    remote_fasttrack_csv = f"{csv_output_dir.rstrip('/')}/{item.batch}_fasttrack.csv"

    if not remote_file_exists(remote_csv):
        print(f"Skipping {item.corpus}/{item.batch}: missing remote batch CSV: {remote_csv}")
        return None

    if not remote_file_exists(remote_fasttrack_csv):
        print(f"Skipping {item.corpus}/{item.batch}: missing remote FastTrack CSV: {remote_fasttrack_csv}")
        return None

    remote_batch_root = f"{output_root.rstrip('/')}/{item.batch}"
    remote_audio_dir = f"{remote_batch_root}/audio"
    remote_images_dir = f"{remote_batch_root}/images"

    rsync_file(remote_csv, local_csv_dir)
    rsync_file(remote_fasttrack_csv, local_csv_dir)
    
    local_csv_path = local_csv_dir / f"{item.batch}.csv"
    normalized_csv_path = local_batch_root / "batch.csv"

    local_fasttrack_csv_path = local_csv_dir / f"{item.batch}_fasttrack.csv"
    normalized_fasttrack_csv_path = local_batch_root / "fasttrack.csv"

    if local_csv_path.exists() and local_csv_path != normalized_csv_path:
        local_csv_path.replace(normalized_csv_path)

    if local_fasttrack_csv_path.exists() and local_fasttrack_csv_path != normalized_fasttrack_csv_path:
        local_fasttrack_csv_path.replace(normalized_fasttrack_csv_path)

    rsync_filtered_dir(
        remote_audio_dir,
        local_audio_dir,
        include_patterns=[
            "*/",
            "*.wav",
            "*.WAV",
            "*.TextGrid",
            "*.textgrid",
        ],
    )

    rsync_filtered_dir(
        remote_images_dir,
        local_images_dir,
        include_patterns=[
            "*/",
            "*.png",
            "*.PNG",
        ],
    )

    return {
        "corpus": item.corpus,
        "batch": item.batch,
        "local_root": str(local_batch_root),
        "csv_path": str(normalized_csv_path),
        "fasttrack_csv_path": str(normalized_fasttrack_csv_path),
        "config_path": str(local_corpus_root / "config" / f"{item.corpus}.yaml"),
        "remote_csv": remote_csv,
        "remote_audio_dir": remote_audio_dir,
        "remote_images_dir": remote_images_dir,
    }

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync assigned formant annotation batches.")
    parser.add_argument("--corpus", required=True, help="Corpus name, for example: ls_eng")
    return parser.parse_args()

def run_ssh(*remote_command: str) -> subprocess.CompletedProcess[str]:
    """Run a remote command and retain its output for useful error reporting."""
    if not REMOTE_USER_HOST:
        raise SystemExit(
            "\nError: REMOTE_USER_HOST is not set.\n"
            "Set it in .env, for example:\n"
            "  REMOTE_USER_HOST=username@oka\n"
        )

    try:
        return subprocess.run(
            ["ssh", REMOTE_USER_HOST, *remote_command],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "\nError: ssh is not installed or is not available on PATH.\n"
        ) from exc


def ssh_detail(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout).strip()
    if not detail:
        detail = f"ssh exited with status {result.returncode}."
    return "\n".join(f"  {line}" for line in detail.splitlines())


def raise_ssh_connection_error(result: subprocess.CompletedProcess[str]) -> None:
    raise SystemExit(
        f"\nError: could not connect to {REMOTE_USER_HOST}.\n\n"
        f"SSH reported:\n{ssh_detail(result)}\n\n"
        f"Check REMOTE_USER_HOST and confirm that `ssh {REMOTE_USER_HOST}` works "
        "from this terminal.\n"
    )


def validate_corpus_exists(corpus: str) -> None:
    """Verify that the remote config directory is accessible and contains corpus."""
    available = available_remote_corpora()

    if not available:
        raise SystemExit(
            "\nError: connected successfully to Oka, but no corpus configuration "
            "files were found in:\n"
            f"  {REMOTE_CONFIG_DIR}\n"
        )

    if corpus not in available:
        raise SystemExit(
            f"\nError: corpus '{corpus}' was not found on Oka.\n"
            f"Remote configuration directory:\n  {REMOTE_CONFIG_DIR}\n\n"
            "Available corpora:\n"
            + "\n".join(f"  - {name}" for name in available)
            + "\n"
        )


def remote_file_exists(remote_path: str) -> bool:
    """Return False only when the remote server confirms that a file is absent."""
    result = run_ssh("ls", "-ld", remote_path)

    if result.returncode == 0:
        return True
    if result.returncode == 255:
        raise_ssh_connection_error(result)

    detail = (result.stderr or result.stdout).lower()
    if "no such file or directory" in detail:
        return False
    if "permission denied" in detail:
        raise SystemExit(
            "\nError: connected to Oka, but could not access the remote path:\n"
            f"  {remote_path}\n\n"
            f"Remote error:\n{ssh_detail(result)}\n"
        )

    raise SystemExit(
        "\nError: could not check the remote path:\n"
        f"  {remote_path}\n\n"
        f"SSH reported:\n{ssh_detail(result)}\n"
    )


def available_remote_corpora() -> list[str]:
    result = run_ssh("ls", "-1", REMOTE_CONFIG_DIR)

    if result.returncode == 255:
        raise_ssh_connection_error(result)

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).lower()
        if "permission denied" in detail:
            raise SystemExit(
                f"\nError: connected to {REMOTE_USER_HOST}, but could not read the "
                "remote corpus configuration directory:\n"
                f"  {REMOTE_CONFIG_DIR}\n\n"
                f"Remote error:\n{ssh_detail(result)}\n\n"
                "Your Oka account may not have access to /projects/xling-measures.\n"
            )
        if "no such file or directory" in detail:
            raise SystemExit(
                f"\nError: connected to {REMOTE_USER_HOST}, but the remote corpus "
                "configuration directory does not exist:\n"
                f"  {REMOTE_CONFIG_DIR}\n\n"
                "Check REMOTE_PROJECT_ROOT in .env.\n"
            )

        raise SystemExit(
            "\nError: could not read the remote corpus configuration directory:\n"
            f"  {REMOTE_CONFIG_DIR}\n\n"
            f"SSH reported:\n{ssh_detail(result)}\n"
        )

    return sorted(
        Path(line).stem
        for line in result.stdout.splitlines()
        if line.endswith(".yaml")
    )

def main() -> None:
    if ANNOTATOR_ID == "unknown":
        raise RuntimeError("Set ANNOTATOR_ID in .env before syncing batches.")

    args = parse_args()
    validate_corpus_exists(args.corpus)
    
    config_path = sync_corpus_config(args.corpus)
    config = load_yaml(config_path)

    assigned_batches = assigned_batches_from_corpus_config(
        corpus=args.corpus,
        config=config,
        annotator_id=ANNOTATOR_ID,
    )

    if not assigned_batches:
        print(f"No batches assigned to annotator {ANNOTATOR_ID!r} in {config_path}")
        return

    manifest = load_manifest()
    manifest["annotator_id"] = ANNOTATOR_ID
    manifest.setdefault("batches", {})

    for item in assigned_batches:
        summary = sync_batch(item, config)

        if summary is None:
            continue

        manifest["batches"][f"{item.corpus}/{item.batch}"] = summary
        print(f"{f'Synced {item.corpus}/{item.batch}':=<70}")

    save_manifest(manifest)
    print(f"Wrote {SYNC_MANIFEST_PATH}")

if __name__ == "__main__":
    main()