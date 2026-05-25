"""
API routes for frontend.
"""

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud
from app.config import ANNOTATOR_ID
from app.database import get_db
from app.models import Token
from app.schemas import (
    AnnotationCreate,
    AnnotationRead,
    ClosePraatRead,
    OpenPraatRead,
    FastTrackRead,
    FastTrackRequest,
    ProgressRead,
    TokenRead,
)
from app.services.praat import (
    PraatConfigurationError,
    PraatFileError,
    PraatProcessError,
    close_app_praat_process,
    open_token_in_praat,
)
from app.services.fasttrack import (
    FastTrackGenerationError,
    FastTrackInputFileError,
    generate_fasttrack_alternative,
    get_temp_fasttrack_image_path,
    promote_fasttrack_alternative,
)

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
        textgrid_url=file_path_to_static_url(token.textgrid_path),
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
        message="Generated alternative FastTrack spectrogram.",
    )

@router.get("/tokens/{token_id}/fasttrack-image")
def get_fasttrack_image(token_id: str) -> FileResponse:
    """
    Stream the temporary FastTrack spectrogram image for one token.

    The image is not stored under app/static because it is temporary backend
    state. The frontend can use this URL as an <img src>.
    """

    image_path = get_temp_fasttrack_image_path(token_id)

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

@router.post("/annotations", response_model=AnnotationRead, status_code=status.HTTP_201_CREATED)
def create_annotation(
    annotation_in: AnnotationCreate,
    db: Session = Depends(get_db),
) -> AnnotationRead:
    """
    Saves one annotation decision.

    If the frontend says the currently displayed image is the FastTrack
    alternative, promote the alternative before saving the annotation.
    """

    try:
        if annotation_in.image_source == "alternate":
            token = crud.get_token_by_id(
                db=db,
                token_id=annotation_in.token_id,
            )

            if token is None:
                raise ValueError(f"Unknown token_id: {annotation_in.token_id}")
            
            promoted = promote_fasttrack_alternative(token=token)

            token.image_path = promoted.image_path_value
            token.candidates_pickle_path = promoted.candidates_pickle_path_value

            if annotation_in.fasttrack_params is not None:
                token.min_max_formant = annotation_in.fasttrack_params.min_max_formant
                token.max_max_formant = annotation_in.fasttrack_params.max_max_formant
                token.n_formants = annotation_in.fasttrack_params.n_formants

            db.add(token)

        annotation = crud.create_annotation(
            db=db,
            annotation_in=annotation_in,
        )

    except FastTrackInputFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

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