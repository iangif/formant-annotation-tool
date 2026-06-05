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
        raise RuntimeError("Set REMOTE_USER_HOST in .env, for example: REMOTE_USER_HOST=username@oka")

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

    subprocess.run(command, check=True)

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
    batch_names = config.get("batches", {}).keys()

    assigned: list[AssignedBatch] = []
    for batch_name in batch_names:
        annotators = config.get(batch_name, [])
        if annotator_id in annotators:
            assigned.append(AssignedBatch(corpus=corpus, batch=str(batch_name)))

    return assigned

def sync_batch(item: AssignedBatch, config: dict[str, Any]) -> dict[str, Any]:
    output_root = config["output_root"]
    csv_output_dir = config["csv_output_dir"]

    local_corpus_root = CORPORA_DIR / item.corpus
    local_batch_root = local_corpus_root / "batches" / item.batch
    local_csv_dir = local_batch_root
    local_audio_dir = local_batch_root / "audio"
    local_images_dir = local_batch_root / "images"

    remote_csv = f"{csv_output_dir.rstrip('/')}/{item.batch}.csv"
    remote_fasttrack_csv = f"{csv_output_dir.rstrip('/')}/{item.batch}_fasttrack.csv"
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

def validate_corpus_exists(corpus: str) -> None:
    """Verify that request corpus has a config file"""
    
    remote_config = f"{REMOTE_USER_HOST}:{REMOTE_CONFIG_DIR}/{corpus}.yaml"

    result = subprocess.run(
        ["ssh", REMOTE_USER_HOST, "test", "-f", f"{REMOTE_CONFIG_DIR}/{corpus}.yaml"],
        capture_output=True,
    )

    if result.returncode != 0:
        available = available_remote_corpora()

        raise SystemExit(
            f"\nError: corpus '{corpus}' does not exist.\n"
            f"Available corpora:\n"
            + "\n".join(f"  - {c}" for c in available)
            + "\n"
        )

def available_remote_corpora() -> list[str]:
    result = subprocess.run(
        ["ssh", REMOTE_USER_HOST, f"ls {REMOTE_CONFIG_DIR}/*.yaml 2>/dev/null"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    corpora = []

    for line in result.stdout.splitlines():
        corpora.append(Path(line).stem)

    return sorted(corpora)

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
        manifest["batches"][f"{item.corpus}/{item.batch}"] = summary
        print(f"{f'Synced {item.corpus}/{item.batch}':=<70}")

    save_manifest(manifest)
    print(f"Wrote {SYNC_MANIFEST_PATH}")

if __name__ == "__main__":
    main()