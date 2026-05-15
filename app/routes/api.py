"""
API routes for frontend.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.config import ANNOTATOR_ID
from app.database import get_db
from app.models import Token
from app.schemas import AnnotationCreate, AnnotationRead, ProgressRead, TokenRead

router = APIRouter(prefix="/api", tags=["api"])

def file_path_to_static_url(path_value: str | None) -> str | None:
    """
    Convert a stored file path into a browser URL:
        app/static/images/1-0-7.png (stored in database)
            -- into --> /static/images/1-0-7.png
    """

    if path_value is None:
        return None

    path_value = path_value.replace("\\", "/")

    if path_value.startswith("/static/"):
        return path_value

    marker = "app/static/"

    if marker in path_value:
        relative_path = path_value.split(marker, maxsplit=1)[1]
        return f"/static/{relative_path}"

    if path_value.startswith("static/"):
        relative_path = path_value.removeprefix("static/")
        return f"/static/{relative_path}"

    return f"/static/{Path(path_value).name}"

def token_to_read(token: Token) -> TokenRead:
    """
    Convert a SQLAlchemy Token model into the API response schema.
    """

    return TokenRead(
        id=token.id,
        corpus=token.corpus,
        speaker_id=token.speaker_id,
        vowel_label=token.vowel_label,
        word=token.word,
        preceding_phone=token.preceding_phone,
        following_phone=token.following_phone,
        duration_ms=token.duration_ms,
        n_candidates=token.n_candidates,
        auto_winner_panel=token.auto_winner_panel,
        image_url=file_path_to_static_url(token.image_path),
        audio_url=file_path_to_static_url(token.audio_path),
    )

@router.get("/tokens/next", response_model=TokenRead | None)
def get_next_token(
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> TokenRead | None:
    """
    Returns the next unannotated token for an annotator.
    Returns null when the annotator has completed all assigned tokens.
    """

    token = crud.get_next_token(db=db, annotator_id=annotator_id)

    if token is None:
        return None
    
    return token_to_read(token)

@router.get("/tokens/{token_id}", response_model=TokenRead)
def get_token(
    token_id: str,
    db: Session = Depends(get_db),
) -> TokenRead:
    """
    Returns one token by ID.
    """

    token = crud.get_token_by_id(db=db, token_id=token_id)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token not found: {token_id}",
        )
    
    return token_to_read(token)

@router.post("/annotations", response_model=AnnotationRead, status_code=status.HTTP_201_CREATED)
def create_annotation(
    annotation_in: AnnotationCreate,
    db: Session = Depends(get_db),
) -> AnnotationRead:
    """
    Saves one annotation decision.
    Called by frontend after every token decision.
    """

    try:
        annotation = crud.create_annotation(
            db=db,
            annotation_in=annotation_in,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return annotation

@router.get("/progress", response_model=ProgressRead)
def get_progress(
    annotator_id: str = Query(default=ANNOTATOR_ID),
    db: Session = Depends(get_db),
) -> ProgressRead:
    """
    Returns annotation progress for one annotator.
    """

    return crud.get_progress(db=db, annotator_id=annotator_id)