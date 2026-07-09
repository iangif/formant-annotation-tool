"""Local web-app wrapper for exporting gold tracks from local upload snapshots.

This uses logic imported from the reusable
``formants_export`` package from the formants repo, then supplies local web-app
paths. This makes the same algorithm usable locally and on oka.

Example:

    uv run python -m scripts.export_gold_local ls_eng batch1

Optional manual adjudication workflow:

    1. Run this once. It creates reconciliation files under:
       exports/reconciliation/{corpus}/{batch}/
    2. If disagreements exist, edit:
       exports/reconciliation/{corpus}/{batch}/adjudication_decisions_template.csv
    3. Re-run the same command. The edited template will be used automatically.

For developer testing, unresolved/blank/invalid adjudication rows can be excluded
instead of raising an error:

    uv run python -m scripts.export_gold_local ls_eng batch1 --ignore-conflicts
"""

from __future__ import annotations

import argparse
from pathlib import Path

from formants_export.adjudicate import create_resolved_annotations
from formants_export.exporter import export_gold_tracks
from formants_export.importer import merge_upload_snapshots
from formants_export.paths import LocalExportPaths
from formants_export.reconcile import reconcile_annotations

try:
    from app.config import PROJECT_ROOT
except Exception:  # pragma: no cover - makes this script importable in tests.
    PROJECT_ROOT = Path.cwd()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local gold-track export using the shared formants_export package."
    )
    parser.add_argument("corpus", help="Corpus name, e.g. ls_eng")
    parser.add_argument("batch", help="Batch name, e.g. batch1")
    parser.add_argument(
        "--adjudication-decisions",
        type=Path,
        default=None,
        help=(
            "Optional override path to an edited adjudication decisions CSV. "
            "By default, uses the template created under "
            "exports/reconciliation/{corpus}/{batch}/."
        ),
    )
    parser.add_argument(
        "--ignore-conflicts",
        action="store_true",
        help=(
            "Developer/testing mode: unresolved, blank, or invalid adjudication "
            "rows are excluded as unresolved_conflict instead of raising an error."
        ),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Local web-app project root. Defaults to app.config.PROJECT_ROOT.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = LocalExportPaths(project_root=args.project_root)

    # For local export, start from the local upload snapshot produced by
    # scripts/upload_annotations.py.
    snapshot_path = paths.upload_snapshot_path(args.corpus, args.batch)
    central_db_path = paths.central_annotations_path
    resolved_db_path = paths.resolved_annotations_path

    # Keep local reconciliation layout consistent with the shared package:
    # exports/reconciliation/{corpus}/{batch}/...
    reconciliation_dir = paths.reconciliation_root / args.corpus / args.batch
    reconciliation_report_path = reconciliation_dir / "reconciliation_report.csv"
    adjudication_decisions_path = (
        args.adjudication_decisions
        if args.adjudication_decisions is not None
        else reconciliation_dir / "adjudication_decisions_template.csv"
    )

    output_root = paths.gold_batch_root(args.corpus, args.batch)

    merge_result = merge_upload_snapshots(
        snapshot_paths=[snapshot_path],
        output_db_path=central_db_path,
    )
    print("Merged local snapshot:")
    for key, value in merge_result.items():
        print(f"  {key}: {value}")

    reconciliation_result = reconcile_annotations(
        central_db_path=central_db_path,
        output_dir=reconciliation_dir,
        corpus=args.corpus,
        batch=args.batch,
    )
    print("Created reconciliation reports:")
    for key, value in reconciliation_result.items():
        print(f"  {key}: {value}")

    resolve_result = create_resolved_annotations(
        central_db_path=central_db_path,
        reconciliation_report_path=reconciliation_report_path,
        adjudication_decisions_path=adjudication_decisions_path,
        output_db_path=resolved_db_path,
        ignore_conflicts=args.ignore_conflicts,
    )
    print("Created resolved annotations DB:")
    for key, value in resolve_result.items():
        print(f"  {key}: {value}")

    export_result = export_gold_tracks(
        resolved_db_path=resolved_db_path,
        pickle_root=paths.pickle_root(args.corpus, args.batch),
        output_root=output_root,
        corpus=args.corpus,
        batch=args.batch,
    )
    print("Exported gold tracks:")
    for key, value in export_result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()