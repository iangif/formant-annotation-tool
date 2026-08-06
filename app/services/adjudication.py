"""Application-facing service for adjudication data, persistence, and previews."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from formants_export.adjudication_proposals import annotation_source_fingerprint
from formants_export.adjudication_queries import (
    get_conflict,
    list_conflict_batches,
    list_conflicts,
)
from formants_export.adjudication_store import (
    get_latest_adjudication,
    list_latest_adjudications,
    map_saved_sources_to_current,
    save_adjudication,
)

from app.config import (
    ADJUDICATION_CENTRAL_DB_PATH,
    ADJUDICATION_DB_PATH,
    ADJUDICATION_MEDIA_ROOT,
)


MEDIA_LAYOUT = {
    "image": ("images", ".png"),
    "audio": ("audio", ".wav"),
}


def _current_conflict(token_id: str) -> dict:
    return get_conflict(
        ADJUDICATION_CENTRAL_DB_PATH,
        token_id=token_id,
    )


def _saved_state(
    *,
    token: dict,
    annotations: list[dict],
    saved: dict | None = None,
) -> tuple[str, dict | None]:
    fingerprint = annotation_source_fingerprint(token, annotations)
    if saved is None:
        saved = get_latest_adjudication(
            ADJUDICATION_DB_PATH,
            token_id=str(token["token_id"]),
        )
    if saved is not None:
        stale = saved["source_fingerprint"] != fingerprint
        saved = {**saved, "stale": stale}
        if not stale and saved.get("sources"):
            mapped_sources = map_saved_sources_to_current(
                saved["sources"],
                annotations,
            )
            if saved["resolution"] in {"choose_annotation", "random_track"}:
                selected = mapped_sources[0]
                saved["chosen_annotator_id"] = str(selected["annotator_id"])
    return fingerprint, saved


def conflicts_for_batch(*, corpus: str, batch: str) -> list[dict]:
    conflicts = list_conflicts(
        ADJUDICATION_CENTRAL_DB_PATH,
        corpus=corpus,
        batch=batch,
    )
    saved_by_token = {
        row["token_id"]: row
        for row in list_latest_adjudications(
            ADJUDICATION_DB_PATH,
            corpus=corpus,
            batch=batch,
        )
    }
    enriched: list[dict] = []
    for conflict in conflicts:
        detail = _current_conflict(str(conflict["token_id"]))
        _, saved = _saved_state(
            token=detail["token"],
            annotations=detail["annotations"],
            saved=saved_by_token.get(conflict["token_id"]),
        )
        if saved is None:
            status = "unresolved"
        elif saved["stale"]:
            status = "stale"
        else:
            status = "saved"
        enriched.append(
            {
                **conflict,
                "adjudication_status": status,
                "saved_resolution": None if saved is None else saved["resolution"],
                "saved_revision": None if saved is None else saved["revision"],
            }
        )
    return enriched


def conflict_batches() -> list[dict]:
    batches = list_conflict_batches(ADJUDICATION_CENTRAL_DB_PATH)
    results: list[dict] = []
    for item in batches:
        conflicts = conflicts_for_batch(
            corpus=str(item["corpus"]),
            batch=str(item["batch"]),
        )
        saved_count = sum(
            conflict["adjudication_status"] == "saved" for conflict in conflicts
        )
        stale_count = sum(
            conflict["adjudication_status"] == "stale" for conflict in conflicts
        )
        results.append(
            {
                **item,
                "saved_count": saved_count,
                "stale_count": stale_count,
                "unresolved_count": len(conflicts) - saved_count - stale_count,
            }
        )
    return results


def _candidate_source_path(
    token: dict,
    *,
    directory: str,
    suffix: str,
) -> Path:
    """Build a contained source path from trusted central token metadata."""

    root = ADJUDICATION_MEDIA_ROOT.expanduser().resolve()
    candidate = (
        root
        / token["corpus"]
        / token["batch"]
        / directory
        / f"{token['file_stem']}{suffix}"
    ).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Central token metadata resolves outside the media root.")
    return candidate


def _candidate_media_path(token: dict, media_kind: str) -> Path:
    directory, suffix = MEDIA_LAYOUT[media_kind]
    return _candidate_source_path(token, directory=directory, suffix=suffix)


def _candidate_pickle_path(token: dict) -> Path:
    return _candidate_source_path(token, directory="pickles", suffix=".pkl")


def _resolved_plotting_frequency(token: dict) -> float:
    value = token.get("max_plotting_frequency")
    return 5500.0 if value is None else float(value)


def _has_valid_plotting_frequency(token: dict) -> bool:
    try:
        return _resolved_plotting_frequency(token) > 0
    except (TypeError, ValueError):
        return False


def conflict_detail(*, token_id: str) -> dict:
    result = _current_conflict(token_id)
    token = result["token"]
    annotations = result["annotations"]
    source_fingerprint, saved = _saved_state(
        token=token,
        annotations=annotations,
    )
    encoded_id = quote(token_id, safe="")

    image_path = _candidate_media_path(token, "image")
    audio_path = _candidate_media_path(token, "audio")
    pickle_path = _candidate_pickle_path(token)

    return {
        **token,
        "max_plotting_frequency": _resolved_plotting_frequency(token),
        "image_url": (
            f"/api/adjudication/media/image?token_id={encoded_id}"
            if image_path.is_file()
            else None
        ),
        "audio_url": (
            f"/api/adjudication/media/audio?token_id={encoded_id}"
            if audio_path.is_file()
            else None
        ),
        "track_preview_available": (
            pickle_path.is_file() and _has_valid_plotting_frequency(token)
        ),
        "source_fingerprint": source_fingerprint,
        "saved_adjudication": saved,
        "annotations": annotations,
    }


def latest_decision(*, token_id: str) -> dict | None:
    """Return the latest saved decision with current staleness state."""

    result = _current_conflict(token_id)
    _, saved = _saved_state(
        token=result["token"],
        annotations=result["annotations"],
    )
    return saved


def save_decision(*, payload: dict) -> dict:
    """Validate and persist one append-only adjudication revision."""

    result = _current_conflict(str(payload["token_id"]))
    saved = save_adjudication(
        ADJUDICATION_DB_PATH,
        token=result["token"],
        annotations=result["annotations"],
        payload=payload,
    )
    return {**saved, "stale": False}


def conflict_media_path(*, token_id: str, media_kind: str) -> Path:
    if media_kind not in MEDIA_LAYOUT:
        raise ValueError(f"Unknown adjudication media kind: {media_kind}")
    result = _current_conflict(token_id)
    path = _candidate_media_path(result["token"], media_kind)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _render_track_preview(*, token: dict, annotation: dict) -> bytes:
    from formants_export.adjudication_rendering import (
        render_selected_track_spectrogram,
    )

    pickle_path = _candidate_pickle_path(token)
    if not pickle_path.is_file():
        raise FileNotFoundError(pickle_path)
    return render_selected_track_spectrogram(
        annotation,
        token,
        pickle_path.parent,
        maximum_frequency=_resolved_plotting_frequency(token),
    )


def annotation_track_preview(*, token_id: str, annotator_id: str) -> bytes:
    result = _current_conflict(token_id)
    annotation = next(
        (
            row
            for row in result["annotations"]
            if row["annotator_id"] == annotator_id
        ),
        None,
    )
    if annotation is None:
        raise ValueError(
            f"Annotator {annotator_id!r} has no current annotation for {token_id}."
        )
    return _render_track_preview(token=result["token"], annotation=annotation)


def draft_track_preview(*, payload: dict) -> bytes:
    result = _current_conflict(str(payload["token_id"]))
    annotation = {key: value for key, value in payload.items() if key != "token_id"}
    return _render_track_preview(token=result["token"], annotation=annotation)
