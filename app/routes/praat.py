from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import ClosePraatRead, OpenPraatRead
from app.services.praat import (
    PraatConfigurationError,
    PraatFileError,
    PraatProcessError,
    close_app_praat_process,
    open_token_in_praat,
)

router = APIRouter(tags=["praat"])


@router.post("/tokens/{token_id}/open-praat", response_model=OpenPraatRead)
def open_praat_for_token(
    token_id: str,
    db: Session = Depends(get_db),
) -> OpenPraatRead:
    """
    Opens the token's wav and TextGrid files in Praat.

    This endpoint is intended for the local annotation app only.
    It launches a desktop application on the same machine that is running the FastAPI backend.
    """

    token = crud.get_token_by_id(db=db, token_id=token_id)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token not found: {token_id}",
        )
    
    try:
        open_token_in_praat(
            audio_path_value=token.audio_path,
            textgrid_path_value=token.textgrid_path,
        )
    
    except PraatConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    
    except PraatFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except PraatProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc

    return OpenPraatRead(
        token_id=token_id,
        opened=True,
        message="Opened token in Praat.",
    )

@router.post("/praat/close", response_model=ClosePraatRead)
def close_praat() -> ClosePraatRead:
    """
    Close the Praat process opened by this app.

    This only targets the Praat process tracked by this FastAPI backend.
    It does not attempt to close unrelated Praat windows the user opened manually.
    """

    try:
        closed = close_app_praat_process()

    except PraatProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    
    if not closed:
        return ClosePraatRead(
            closed=False,
            message="No app-opened Praat process is currently running.",
        )
    
    return ClosePraatRead(
        closed=True,
        message="Closed app-opened Praat process.",
    )