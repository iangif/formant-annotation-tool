from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import TokenNoteCreate, TokenNoteRead

router = APIRouter(prefix="/notes", tags=["notes"])


@router.put("", response_model=TokenNoteRead)
def upsert_token_note(
    note_in: TokenNoteCreate,
    db: Session = Depends(get_db),
) -> TokenNoteRead:
    """Create or replace the mutable note for one token/annotator pair."""

    try:
        return crud.upsert_token_note(db=db, note_in=note_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
