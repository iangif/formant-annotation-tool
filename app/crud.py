"""
Defines database operations.

1. Find the next token assigned to an annotator
2. Save an annotation
3. Report annotation progress
"""

from sqlalchemy import func, select, exists
from sqlalchemy.orm import Session

from app.models import Annotation, Token, TokenAssignment
from app.schemas import AnnotationCreate

def get_next_token(db: Session, annotator_id: str) -> Token | None:
    """
    Returns the next token assigned to given annotator that has not
    already been annotated by given annotator.
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

def create_annotation(db: Session, annotation_in: AnnotationCreate) -> Annotation:
    """
    Saves one annotation row to the database.
    """

    # Convert Pydantic object into Annotation model
    annotation = Annotation(**annotation_in.model_dump())

    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    return annotation

def get_progress(db: Session, annotator_id: str) -> dict:
    """
    Return simple progress information for one annotator.

    Output example:
        {
            "annotator_id": "ian",
            "assigned_total": 100,
            "annotated_total": 41,
            "remaining_total": 59
        }
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