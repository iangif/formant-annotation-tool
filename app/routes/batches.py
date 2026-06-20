from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.config import ANNOTATOR_ID
from app.database import get_db
from app.schemas import BatchProgressRead, BatchTokenRead, TokenSummaryRead
from app.services.local_settings import get_last_opened_batch_id, set_last_opened_batch_id
from app.routes.utils import token_to_batch_read

router = APIRouter(prefix="/batches", tags=["batches"])

@router.get("", response_model=list[BatchProgressRead])
def get_batches(
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> list[BatchProgressRead]:
    """Returns all batches assigned to the annotator with progress metadata."""

    last_opened_batch_id = get_last_opened_batch_id(annotator_id)

    return crud.get_assigned_batches_with_progress(
        db=db,
        annotator_id=annotator_id,
        last_opened_batch_id=last_opened_batch_id,
    )

@router.get("/{batch_id}/tokens", response_model=list[TokenSummaryRead])
def get_batch_tokens(
    batch_id: int,
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> list[TokenSummaryRead]:
    """Return summary information and annotation status for tokens in a batch."""

    if not crud.is_batch_assigned(db, batch_id, annotator_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Batch {batch_id} is not assigned to annotator {annotator_id}.",
        )

    return crud.get_batch_token_summaries(
        db=db,
        batch_id=batch_id,
        annotator_id=annotator_id,
    )

@router.get("/{batch_id}/tokens/{index}", response_model=BatchTokenRead)
def get_batch_token_by_index(
    batch_id: int,
    index: int,
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> BatchTokenRead:
    """
    Returns the token at a stable CSV/import index (batch_index).
    """

    if not crud.is_batch_assigned(db, batch_id, annotator_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Batch {batch_id} is not assigned to annotator {annotator_id}.",
        )

    token = crud.get_batch_token_at_index(db, batch_id, index)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No token found for batch {batch_id} at index {index}.",
        )

    latest = crud.latest_annotation_for_token(db, token.token_id, annotator_id)
    note = crud.latest_note_for_token(db, token.token_id, annotator_id)
    return token_to_batch_read(token, latest, note)

@router.post("/{batch_id}/last-opened")
def mark_batch_last_opened(
    batch_id: int,
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> dict:
    """Persist the annotator's most recently opened batch."""

    if not crud.is_batch_assigned(db, batch_id, annotator_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Batch {batch_id} is not assigned to annotator {annotator_id}.",
        )

    set_last_opened_batch_id(annotator_id, batch_id)

    return {
        "annotator_id": annotator_id,
        "batch_id": batch_id,
        "saved": True,
    }