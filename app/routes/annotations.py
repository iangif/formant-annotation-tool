from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import AnnotationCreate, AnnotationRead
from app.services.fasttrack import FastTrackInputFileError, promote_fasttrack_alternative

router = APIRouter(prefix="/annotations", tags=["annotations"])

@router.post("", response_model=AnnotationRead, status_code=status.HTTP_201_CREATED)
def create_annotation(
    annotation_in: AnnotationCreate,
    db: Session = Depends(get_db),
) -> AnnotationRead:
    try:
        if annotation_in.image_source == "alternate":
            token = crud.get_token_by_id(db=db, token_id=annotation_in.token_id)

            if token is None:
                raise ValueError(f"Unknown token_id: {annotation_in.token_id}")

            promoted = promote_fasttrack_alternative(
                token=token,
                cache_key=annotation_in.fasttrack_cache_key,
            )

            token.image_path = promoted.image_path_value
            token.candidates_pickle_path = promoted.candidates_pickle_path_value

            if annotation_in.fasttrack_params is not None:
                token.min_max_formant = annotation_in.fasttrack_params.min_max_formant
                token.max_max_formant = annotation_in.fasttrack_params.max_max_formant
                token.n_formants = annotation_in.fasttrack_params.n_formants

            if annotation_in.displayed_auto_winner_panel is not None:
                token.auto_winner_panel = annotation_in.displayed_auto_winner_panel

            db.add(token)
            db.flush()

        return crud.create_annotation(db=db, annotation_in=annotation_in)

    except FastTrackInputFileError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc