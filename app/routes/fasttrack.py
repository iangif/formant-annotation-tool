from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import FastTrackRead, FastTrackRequest
from app.services.fasttrack import (
    FastTrackGenerationError,
    FastTrackInputFileError,
    generate_fasttrack_alternative,
    get_temp_fasttrack_image_path,
)

router = APIRouter(tags=["fasttrack"])


@router.post("/tokens/{token_id}/fasttrack", response_model=FastTrackRead)
def rerun_fasttrack_for_token(
    token_id: str,
    params: FastTrackRequest,
    db: Session = Depends(get_db),
) -> FastTrackRead:
    """
    Rerun FastTrackPy for the current token and create one alternative spectrogram image.

    This endpoint does not overwrite the committed/original image. It only writes to the alternative image/pickle locations. The frontend can display the returned alternate_image_url immediately.
    """

    token = crud.get_token_by_id(db=db, token_id=token_id)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token not found: {token_id}",
        )

    try:
        result = generate_fasttrack_alternative(
            token=token,
            params=params,
        )

    except FastTrackInputFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except FastTrackGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return FastTrackRead(
        token_id=token_id,
        alternate_image_url=result.image_url,
        auto_winner_panel=result.auto_winner_panel,
        cache_key=result.cache_key,
        message="Generated alternative FastTrack spectrogram.",
    )

@router.get("/tokens/{token_id}/fasttrack-image")
def get_fasttrack_image(token_id: str, cache_key: str | None = None) -> FileResponse:
    """
    Stream the temporary FastTrack spectrogram image for one token.

    The image is not stored under app/static because it is temporary backend
    state. The frontend can use this URL as an <img src>.
    """

    image_path = get_temp_fasttrack_image_path(token_id, cache_key)

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No temporary FastTrack image exists for token {token_id}.",
        )

    return FileResponse(
        path=image_path,
        media_type="image/png",
        filename=f"{token_id}.png",
    )