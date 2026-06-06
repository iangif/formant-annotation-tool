"""
Defines database operations for tokens, batches, assignments, and annotations.

This module is FastAPI-independent and can be used
from API routes, scripts, tests, and future command-line utilities.
"""

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import Annotation, AnnotationDecision, Assignment, Batch, Token
from app.schemas import AnnotationCreate

def get_token_by_id(db: Session, token_id: str) -> Token | None:
    """Returns a token by its id."""
    return db.get(Token, token_id)

def latest_annotation_for_token(
    db: Session,
    token_id: str,
    annotator_id: str,
) -> Annotation | None:
    """Returns the most recent annotation for a token by a specific annotator."""
    stmt = (
        select(Annotation)
        .where(Annotation.token_id == token_id)
        .where(Annotation.annotator_id == annotator_id)
        .order_by(Annotation.created_at.desc(), Annotation.id.desc())
        .limit(1)
    )
    return db.scalar(stmt)

def annotation_history_for_token(
    db: Session,
    token_id: str,
    annotator_id: str,
) -> list[Annotation]:
    """Returns all annotations for a token by an annotator, newest first."""
    stmt = (
        select(Annotation)
        .where(Annotation.token_id == token_id)
        .where(Annotation.annotator_id == annotator_id)
        .order_by(Annotation.created_at.desc(), Annotation.id.desc())
    )
    return list(db.scalars(stmt))

def is_batch_assigned(db: Session, batch_id: int, annotator_id: str) -> bool:
    """Checks whether a batch is assigned to a given annotator."""
    stmt = (
        select(Assignment.id)
        .where(Assignment.batch_id == batch_id)
        .where(Assignment.annotator_id == annotator_id)
        .limit(1)
    )
    return db.scalar(stmt) is not None

def is_token_assigned(db: Session, token_id: str, annotator_id: str) -> bool:
    """Checks whether a token belongs to a batch assigned to a given annotator."""
    stmt = (
        select(Assignment.id)
        .join(Token, Token.batch_id == Assignment.batch_id)
        .where(Token.id == token_id)
        .where(Assignment.annotator_id == annotator_id)
        .limit(1)
    )
    return db.scalar(stmt) is not None

def get_next_token(db: Session, annotator_id: str) -> Token | None:
    """
    Returns the lowest-index unannotated token across assigned batches.
    """

    annotated = (
        select(Annotation.id)
        .where(Annotation.token_id == Token.id)
        .where(Annotation.annotator_id == annotator_id)
        .exists()
    )
    
    stmt = (
        select(Token)
        .join(Assignment, Assignment.batch_id == Token.batch_id)
        .where(Assignment.annotator_id == annotator_id)
        .where(~annotated)
        .order_by(Token.batch_id, Token.batch_index)
        .limit(1)
    )
    return db.scalar(stmt)

def get_assigned_batches_with_progress(
    db: Session,
    annotator_id: str,
    last_opened_batch_id: int | None = None,
) -> list[dict]:
    """Returns assigned batches along with annotation progress statistics."""

    batches = db.scalars(
        select(Batch)
        .join(Assignment, Assignment.batch_id == Batch.id)
        .where(Assignment.annotator_id == annotator_id)
        .order_by(Batch.id)
    ).all()

    results: list[dict] = []

    for batch in batches:
        total_count = db.scalar(
            select(func.count(Token.id)).where(Token.batch_id == batch.id)
        ) or 0

        completed_count = db.scalar(
            select(func.count(distinct(Annotation.token_id)))
            .join(Token, Token.id == Annotation.token_id)
            .where(Token.batch_id == batch.id)
            .where(Annotation.annotator_id == annotator_id)
        ) or 0

        annotated_exists = (
            select(Annotation.id)
            .where(Annotation.token_id == Token.id)
            .where(Annotation.annotator_id == annotator_id)
            .exists()
        )

        first_unfinished_index = db.scalar(
            select(Token.batch_index)
            .where(Token.batch_id == batch.id)
            .where(~annotated_exists)
            .order_by(Token.batch_index)
            .limit(1)
        )

        results.append(
            {
                "id": batch.id,
                "corpus": batch.corpus.name,
                "name": batch.name,
                "completed_count": completed_count,
                "total_count": total_count,
                "remaining_count": total_count - completed_count,
                "first_unfinished_index": first_unfinished_index,
                "is_last_opened": batch.id == last_opened_batch_id,
            }
        )
    
    return results

def get_batch_token_summaries(
    db: Session,
    batch_id: int,
    annotator_id: str,
) -> list[dict]:
    """Returns token metadata and annotation status for a batch."""

    tokens = db.scalars(
        select(Token)
        .where(Token.batch_id == batch_id)
        .order_by(Token.batch_index)
    ).all()

    summaries: list[dict] = []

    for token in tokens:
        latest = latest_annotation_for_token(db, token.id, annotator_id)

        summaries.append(
            {
                "id": token.id,
                "token_id": token.token_id,
                "batch_id": token.batch_id,
                "batch_index": token.batch_index,
                "file_stem": token.file_stem,
                "phone": token.phone,
                "ipa": token.ipa,
                "word": token.word,
                "speaker": token.speaker,
                "is_annotated": latest is not None,
                "latest_decision": latest.decision if latest else None,
            }
        )

    return summaries

def get_batch_token_at_index(
    db: Session,
    batch_id: int,
    batch_index: int,
) -> Token | None:
    """Returns the token at a specific index within a batch."""

    stmt = (
        select(Token)
        .where(Token.batch_id == batch_id)
        .where(Token.batch_index == batch_index)
        .limit(1)
    )
    return db.scalar(stmt)

def create_annotation(db: Session, annotation_in: AnnotationCreate) -> Annotation:
    """
    Saves one annotation row to the database.

    The frontend decides whether the annotation is accept_auto, select_panel,
    complex, bad_token, or needs_correction.

    The backend still enforces invariants:
    - token must exist
    - token must be assigned to this annotator
    - accept_auto always stores the auto_winner_panel
    - select_panel can never duplicate auto_accept
    - complex must contain at least two distinct panel values
    """

    token = get_token_by_id(db, annotation_in.token_id)

    if token is None:
        raise ValueError(f"Unknown token_id: {annotation_in.token_id}")

    if not is_token_assigned(db, annotation_in.token_id, annotation_in.annotator_id):
        raise ValueError(
            f"Token {annotation_in.token_id} is not assigned to annotator "
            f"{annotation_in.annotator_id}"
        )

    data = annotation_in.model_dump(
        exclude={
            "image_source",
            "fasttrack_params",
            "fasttrack_cache_key",
            "displayed_auto_winner_panel",
        }
    )

    winner = token.auto_winner_panel

    if annotation_in.decision == AnnotationDecision.accept_auto:
        data["selected_panel"] = winner
        data["panel_f1"] = winner
        data["panel_f2"] = winner
        data["panel_f3"] = winner
        data["panel_f4"] = winner

    elif annotation_in.decision == AnnotationDecision.select_panel:
        panel = annotation_in.selected_panel

        if panel == winner:
            raise ValueError("select_panel cannot use the auto-winner panel. Use accept_auto instead.")

        data["panel_f1"] = panel
        data["panel_f2"] = panel
        data["panel_f3"] = panel
        data["panel_f4"] = panel

    elif annotation_in.decision == AnnotationDecision.complex:
        panels = [annotation_in.panel_f1, annotation_in.panel_f2, annotation_in.panel_f3, annotation_in.panel_f4]

        if all(panel is None for panel in panels):
            raise ValueError("At least one F1-F4 panel value is required.")

        if all(panel == winner for panel in panels):
            raise ValueError("complex cannot duplicate accept_auto. Use accept_auto instead.")

        non_null_panels = [panel for panel in panels if panel is not None]

        if len(non_null_panels) == 4 and len(set(non_null_panels)) == 1:
            raise ValueError("complex with four identical panels should be select_panel instead.")

        data["selected_panel"] = None

    annotation = Annotation(**data)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    return annotation

def get_progress(db: Session, annotator_id: str) -> dict:
    """Returns assignment and completion counts for an annotator."""

    assigned_token_count = db.scalar(
        select(func.count(Token.id))
        .join(Assignment, Assignment.batch_id == Token.batch_id)
        .where(Assignment.annotator_id == annotator_id)
    ) or 0

    annotated_token_count = db.scalar(
        select(func.count(distinct(Annotation.token_id)))
        .where(Annotation.annotator_id == annotator_id)
    ) or 0

    return {
        "annotator_id": annotator_id,
        "assigned_total": assigned_token_count,
        "annotated_total": annotated_token_count,
        "remaining_total": assigned_token_count - annotated_token_count,
    }