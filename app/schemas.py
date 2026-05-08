"""
Defines Pydantic request/response models
"""

from datetime import datetime
from pydantic import BaseModel
from app.models import AnnotationDecision

class TokenRead(BaseModel):
    id: str
    corpus: str
    speaker_id: str | None = None
    vowel_label: str
    word: str | None = None
    image_url: str
    audio_url: str | None = None
    auto_winner_panel: int | None = None

class AnnotationCreate(BaseModel):
    token_id: str
    annotator_id: str
    decision: AnnotationDecision
    selected_panel: int | None = None
    panel_f1: int | None = None
    panel_f2: int | None = None
    panel_f3: int | None = None
    panel_f4: int | None = None
    notes: str | None = None

class AnnotationRead(AnnotationCreate):
    id: int
    created_at: datetime
    annotation_version: str