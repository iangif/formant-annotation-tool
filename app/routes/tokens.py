from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.config import ANNOTATOR_ID
from app.database import get_db
from app.schemas import AnnotationRead, TokenRead
from app.routes.utils import token_to_read

router = APIRouter(prefix="/tokens", tags=["tokens"])

@router.get("/{token_id}", response_model=TokenRead)
def get_token(
    token_id: str,
    db: Session = Depends(get_db),
) -> TokenRead:
    """Returns a token by ID, or raises 404 if it does not exist."""
    token = crud.get_token_by_id(db=db, token_id=token_id)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token not found: {token_id}",
        )

    return token_to_read(token)

@router.get("/{token_id}/latest-annotation", response_model=AnnotationRead | None)
def get_latest_annotation(
    token_id: str,
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> AnnotationRead | None:
    """Returns the annotator's latest annotation for an assigned token."""

    if not crud.is_token_assigned(db, token_id, annotator_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token {token_id} is not assigned to annotator {annotator_id}.",
        )

    return crud.latest_annotation_for_token(db, token_id, annotator_id)

@router.get("/{token_id}/annotations", response_model=list[AnnotationRead])
def get_annotation_history(
    token_id: str,
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> list[AnnotationRead]:
    """Return the annotator's annotation history for an assigned token."""

    if not crud.is_token_assigned(db, token_id, annotator_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token {token_id} is not assigned to annotator {annotator_id}.",
        )

    return crud.annotation_history_for_token(db, token_id, annotator_id)