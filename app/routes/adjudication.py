"""HTTP routes for browsing, previewing, and saving conflict resolutions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, Response

from formants_export.adjudication_queries import (
    CentralDatabaseError,
    ConflictNotFoundError,
)
from formants_export.adjudication_store import (
    AdjudicationRevisionConflictError,
    StaleAdjudicationError,
)

from app.adjudication_schemas import (
    AdjudicationSaveRequest,
    AutomaticProposalRead,
    AutomaticProposalRequest,
    ConflictBatchRead,
    ConflictDetailRead,
    ConflictSummaryRead,
    DraftTrackPreviewRequest,
    SavedAdjudicationRead,
)
from app.services import adjudication
from app.services import adjudication_proposals


router = APIRouter(prefix="/adjudication", tags=["adjudication"])


def _service_error(error: Exception) -> HTTPException:
    if isinstance(error, ConflictNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(error, FileNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adjudication media file not found: {error}",
        )
    if isinstance(error, (AdjudicationRevisionConflictError, StaleAdjudicationError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    if isinstance(error, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("/batches", response_model=list[ConflictBatchRead])
def get_conflict_batches() -> list[dict]:
    """List corpus/batch pairs that have at least one current conflict."""

    try:
        return adjudication.conflict_batches()
    except CentralDatabaseError as error:
        raise _service_error(error) from error


@router.get("/conflicts", response_model=list[ConflictSummaryRead])
def get_conflicts(
    corpus: str = Query(min_length=1),
    batch: str = Query(min_length=1),
) -> list[dict]:
    """List current conflicts for a selected corpus and batch."""

    try:
        return adjudication.conflicts_for_batch(corpus=corpus, batch=batch)
    except CentralDatabaseError as error:
        raise _service_error(error) from error


@router.get("/conflict", response_model=ConflictDetailRead)
def get_conflict_detail(
    token_id: str = Query(min_length=1),
) -> dict:
    """Return all current annotations and display metadata for one conflict."""

    try:
        return adjudication.conflict_detail(token_id=token_id)
    except (CentralDatabaseError, ConflictNotFoundError, ValueError) as error:
        raise _service_error(error) from error


@router.get("/media/{media_kind}")
def get_conflict_media(
    media_kind: str,
    token_id: str = Query(min_length=1),
) -> FileResponse:
    """Serve candidate image or audio for a current conflict."""

    try:
        path = adjudication.conflict_media_path(
            token_id=token_id,
            media_kind=media_kind,
        )
    except (
        CentralDatabaseError,
        ConflictNotFoundError,
        FileNotFoundError,
        ValueError,
    ) as error:
        raise _service_error(error) from error

    media_type = "image/png" if media_kind == "image" else "audio/wav"
    return FileResponse(path=path, media_type=media_type, filename=path.name)


def _png_response(content: bytes) -> Response:
    """Return a generated preview that browsers must not treat as persisted."""

    return Response(
        content=content,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/track-preview")
def get_annotation_track_preview(
    token_id: str = Query(min_length=1),
    annotator_id: str = Query(min_length=1),
) -> Response:
    """Render one current annotation over a clean token spectrogram."""

    try:
        content = adjudication.annotation_track_preview(
            token_id=token_id,
            annotator_id=annotator_id,
        )
    except Exception as error:
        raise _service_error(error) from error
    return _png_response(content)


@router.post("/draft-preview")
def post_draft_track_preview(
    payload: DraftTrackPreviewRequest,
) -> Response:
    """Render an unsaved browser draft without storing any decision."""

    try:
        content = adjudication.draft_track_preview(
            payload=payload.model_dump(),
        )
    except Exception as error:
        raise _service_error(error) from error
    return _png_response(content)


@router.get("/decision", response_model=SavedAdjudicationRead | None)
def get_latest_adjudication_decision(
    token_id: str = Query(min_length=1),
) -> dict | None:
    """Return the latest saved revision and whether its sources are stale."""

    try:
        return adjudication.latest_decision(token_id=token_id)
    except Exception as error:
        raise _service_error(error) from error


@router.post("/decision", response_model=SavedAdjudicationRead)
def post_adjudication_decision(
    payload: AdjudicationSaveRequest,
) -> dict:
    """Validate and append one persistent adjudication revision."""

    try:
        return adjudication.save_decision(payload=payload.model_dump())
    except Exception as error:
        raise _service_error(error) from error


@router.post("/automatic-proposal", response_model=AutomaticProposalRead)
def post_automatic_proposal(
    payload: AutomaticProposalRequest,
) -> dict:
    """Describe a random/average proposal without storing it."""

    try:
        return adjudication_proposals.automatic_proposal(
            payload=payload.model_dump(),
        )
    except Exception as error:
        raise _service_error(error) from error


@router.post("/automatic-preview")
def post_automatic_proposal_preview(
    payload: AutomaticProposalRequest,
) -> Response:
    """Render the same automatic recipe used by final resolution."""

    try:
        content = adjudication_proposals.automatic_proposal_preview(
            payload=payload.model_dump(),
        )
    except Exception as error:
        raise _service_error(error) from error
    return _png_response(content)
