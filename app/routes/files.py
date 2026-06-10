from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud
from app.config import PROJECT_ROOT
from app.database import get_db

router = APIRouter(prefix="/files", tags=["files"])

def resolve_local_data_path(path_value: str | None) -> Path:
    if path_value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File path is missing.",
        )

    path = Path(path_value)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}",
        )

    return path

@router.get("/tokens/{token_id}/image")
def get_token_image(
    token_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Returns image associated with a given token id."""

    token = crud.get_token_by_id(db, token_id)

    if token is None:
        raise HTTPException(status_code=404, detail=f"Token not found: {token_id}")

    path = resolve_local_data_path(token.image_path)

    return FileResponse(
        path=path,
        media_type="image/png",
        filename=path.name,
    )

@router.get("/tokens/{token_id}/audio")
def get_token_audio(
    token_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Returns audio file associated with a given token id."""

    token = crud.get_token_by_id(db, token_id)

    if token is None:
        raise HTTPException(status_code=404, detail=f"Token not found: {token_id}")

    path = resolve_local_data_path(token.audio_path)

    return FileResponse(
        path=path,
        media_type="audio/wav",
        filename=path.name,
    )

@router.get("/tokens/{token_id}/textgrid")
def get_token_textgrid(
    token_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Returns TextGrid file associated with a given token id."""

    token = crud.get_token_by_id(db, token_id)

    if token is None:
        raise HTTPException(status_code=404, detail=f"Token not found: {token_id}")

    path = resolve_local_data_path(token.textgrid_path)

    return FileResponse(
        path=path,
        media_type="text/plain",
        filename=path.name,
    )