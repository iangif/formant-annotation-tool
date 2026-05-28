"""
Defines database operations.

This module is FastAPI-independent and can be used
from API routes, scripts, tests, and future command-line utilities.
"""

from sqlalchemy import func, select, exists
from sqlalchemy.orm import Session

from app.models import Annotation, AnnotationDecision, Token, TokenAssignment
from app.schemas import AnnotationCreate

def get_next_token(db: Session, annotator_id: str) -> Token | None:
    """
    Returns the next token assigned to annotator_id that has not already been annotated by annotator_id.
    """

    # Condition whether annotation exists for this token by this annotator
    already_annotated = (
        select(Annotation.id)
        .where(Annotation.token_id == Token.id)
        .where(Annotation.annotator_id == annotator_id)
        .exists()
    )

    # Search Token table for tokens not annotated by annotator
    stmt = (
        select(Token)
        .join(TokenAssignment, TokenAssignment.token_id == Token.id)
        .where(TokenAssignment.annotator_id == annotator_id)
        .where(~already_annotated)
        .order_by(Token.id)
        .limit(1)
    )

    return db.scalar(stmt)

def get_token_by_id(db: Session, token_id: str) -> Token | None:
    """
    Returns a token by ID, or None if it does not exist.
    """
    
    stmt = select(Token).where(Token.id == token_id)
    return db.scalar(stmt)

def is_token_assigned(db: Session, token_id: str, annotator_id: str) -> bool:
    """
    Returns True if the token is assigned to this annotator.
    """

    stmt = (
        select(TokenAssignment.id)
        .where(TokenAssignment.token_id == token_id)
        .where(TokenAssignment.annotator_id == annotator_id)
        .limit(1)
    )

    return db.scalar(stmt) is not None

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

    if not is_token_assigned(db=db, token_id=annotation_in.token_id, annotator_id=annotation_in.annotator_id):
        raise ValueError(f"Token {annotation_in.token_id} is not assigned to annotator {annotation_in.annotator_id}")
    
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
        panels = [
            annotation_in.panel_f1,
            annotation_in.panel_f2,
            annotation_in.panel_f3,
            annotation_in.panel_f4,
        ]
        
        if all(panel is None for panel in panels):
            raise ValueError(
                "At least one F1-F4 panel value is required. "
            )

        if all(panel == winner for panel in panels):
            raise ValueError(
                "complex cannot duplicate auto_accept. "
                "Use auto_accept instead."
            )

        non_null_panels = [panel for panel in panels if panel is not None]

        if (len(non_null_panels) == 4 and len(set(non_null_panels)) == 1):
            raise ValueError(
                "complex with four identical panels should be select_panel instead."
            )

        data["selected_panel"] = None

    annotation = Annotation(**data)

    db.add(annotation)
    # Open question: how to handle if token is already annotated?
    # Currently, a new annotation is added with a different date.
    db.commit()
    db.refresh(annotation)

    return annotation

def get_progress(db: Session, annotator_id: str) -> dict:
    """
    Return simple progress information for one annotator.
    """
    assigned_total_stmt = (
        select(func.count())
        .select_from(TokenAssignment)
        .where(TokenAssignment.annotator_id == annotator_id)
    )

    annotated_total_stmt = (
        select(func.count())
        .select_from(Annotation)
        .where(Annotation.annotator_id == annotator_id)
    )

    assigned_total = db.scalar(assigned_total_stmt) or 0
    annotated_total = db.scalar(annotated_total_stmt) or 0

    return {
        "annotator_id": annotator_id,
        "assigned_total": assigned_total,
        "annotated_total": annotated_total,
        "remaining_total": assigned_total - annotated_total,
    }