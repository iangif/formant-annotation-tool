"""HTTP routes for browsing current annotation conflicts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from formants_export.adjudication_queries import (
    CentralDatabaseError,
    ConflictNotFoundError,
)

from app.adjudication_schemas import (
    ConflictBatchRead,
    ConflictDetailRead,
    ConflictSummaryRead,
)
from app.services import adjudication

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
