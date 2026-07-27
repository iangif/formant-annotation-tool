"""Application-facing service for adjudication data, media, and previews."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from formants_export.adjudication_queries import (
    get_conflict,
    list_conflict_batches,
    list_conflicts,
)
from formants_export.adjudication_rendering import (
    render_selected_track_spectrogram,
)

from app.config import ADJUDICATION_CENTRAL_DB_PATH, ADJUDICATION_MEDIA_ROOT


MEDIA_LAYOUT = {
    "image": ("images", ".png"),
    "audio": ("audio", ".wav"),
}


def conflict_batches() -> list[dict]:
    return list_conflict_batches(ADJUDICATION_CENTRAL_DB_PATH)


def conflicts_for_batch(*, corpus: str, batch: str) -> list[dict]:
    return list_conflicts(
        ADJUDICATION_CENTRAL_DB_PATH,
        corpus=corpus,
        batch=batch,
    )


def _candidate_source_path(
    token: dict,
    *,
    directory: str,
    suffix: str,
) -> Path:
    """Build a source path from trusted central token metadata.

    The resolved-path containment check prevents unexpected corpus, batch, or
    file-stem values from escaping the configured media root.
    """

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
    return _candidate_source_path(
        token,
        directory=directory,
        suffix=suffix,
    )


def _candidate_pickle_path(token: dict) -> Path:
    return _candidate_source_path(
        token,
        directory="pickles",
        suffix=".pkl",
    )


def _resolved_plotting_frequency(token: dict) -> float:
    """Temporarily supply a ceiling for snapshots lacking this metadata."""

    value = token.get("max_plotting_frequency")
    if value is None:
        return 5500.0 # DEFAULT MAX PLOTTING FREQUENCY

    return float(value)


def _has_valid_plotting_frequency(token: dict) -> bool:
    try:
        return _resolved_plotting_frequency(token) > 0
    except (TypeError, ValueError):
        return False


def conflict_detail(*, token_id: str) -> dict:
    result = get_conflict(
        ADJUDICATION_CENTRAL_DB_PATH,
        token_id=token_id,
    )
    token = result["token"]
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
        "annotations": result["annotations"],
    }


def conflict_media_path(*, token_id: str, media_kind: str) -> Path:
    if media_kind not in MEDIA_LAYOUT:
        raise ValueError(f"Unknown adjudication media kind: {media_kind}")

    result = get_conflict(
        ADJUDICATION_CENTRAL_DB_PATH,
        token_id=token_id,
    )
    path = _candidate_media_path(result["token"], media_kind)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _render_track_preview(*, token: dict, annotation: dict) -> bytes:
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
    """Render one current annotator's composite selected track."""

    result = get_conflict(
        ADJUDICATION_CENTRAL_DB_PATH,
        token_id=token_id,
    )
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
    return _render_track_preview(
        token=result["token"],
        annotation=annotation,
    )


def draft_track_preview(*, payload: dict) -> bytes:
    """Render a browser draft without writing it to application storage."""

    result = get_conflict(
        ADJUDICATION_CENTRAL_DB_PATH,
        token_id=payload["token_id"],
    )
    annotation = {
        key: value
        for key, value in payload.items()
        if key != "token_id"
    }
    return _render_track_preview(
        token=result["token"],
        annotation=annotation,
    )
