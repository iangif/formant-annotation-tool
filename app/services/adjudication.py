"""Application-facing service for read-only adjudication data and media."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from formants_export.adjudication_queries import (
    get_conflict,
    list_conflict_batches,
    list_conflicts,
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


def _candidate_media_path(token: dict, media_kind: str) -> Path:
    """Build a media path from trusted central token metadata.

    The resolved-path containment check prevents unexpected corpus, batch, or
    file-stem values from escaping the configured media root.
    """

    directory, suffix = MEDIA_LAYOUT[media_kind]
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


def conflict_detail(*, token_id: str) -> dict:
    result = get_conflict(
        ADJUDICATION_CENTRAL_DB_PATH,
        token_id=token_id,
    )
    token = result["token"]
    encoded_id = quote(token_id, safe="")

    image_path = _candidate_media_path(token, "image")
    audio_path = _candidate_media_path(token, "audio")

    return {
        **token,
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
