"""
Defines Pydantic request/response schemas.

These models define the API contract:
- what the frontend receives
- what the frontend sends
- what the backend validates before writing to database
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator, Field
from app.models import AnnotationDecision

MIN_PANEL = 0
MAX_PANEL = 19

class TokenRead(BaseModel):
    """
    Token data returned to the frontend.
    Note: image_url and audio_url are browser URLs, not filesystem paths
    """

    id: str
    corpus: str
    speaker_id: str | None = None
    vowel_label: str
    word: str | None = None
    preceding_phone: str | None = None
    following_phone: str | None = None
    duration_ms: float | None = None

    n_candidates: int
    auto_winner_panel: int

    image_url: str
    audio_url: str | None = None
    textgrid_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

class OpenPraatRead(BaseModel):
    """
    Response returned after the backend asks Praat to open a token.
    """

    token_id: str
    opened: bool
    message: str

class AnnotationCreate(BaseModel):
    """
    Payload sent by the frontend when the annotator makes a decision.
    """

    token_id: str
    annotator_id: str
    decision: AnnotationDecision

    selected_panel: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f1: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f2: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f3: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f4: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)

    notes: str | None = None

    @model_validator(mode="after")
    def validate_panel_fields(self) -> "AnnotationCreate":
        """
        Validate decision-specific panel requirements.

        accept_auto:
            Panel fields are optional because the backend fills them from token.auto_winner_panel.

        select_panel:
            selected_panel is required.
        
        complex:
            all four formant panel fields are required.

        bad_token / needs_correction:
            panel fields are optional.
        """

        if self.decision == AnnotationDecision.select_panel:
            if self.selected_panel is None:
                raise ValueError("selected_panel is required for select_panel")
        
        if self.decision == AnnotationDecision.complex:
            panels = [self.panel_f1, self.panel_f2, self.panel_f3, self.panel_f4]

            if any(panel is None for panel in panels):
                raise ValueError("panel_f1 through panel_f4 are required for complex")

            if len(set(panels)) == 1:
                raise ValueError("complex requires at least one differing panel")

        return self

class AnnotationRead(AnnotationCreate):
    """
    Annotation row returned after a successful save.
    """
    id: int
    token_id: str
    annotator_id: str
    decision: AnnotationDecision

    selected_panel: int | None = None
    panel_f1: int | None = None
    panel_f2: int | None = None
    panel_f3: int | None = None
    panel_f4: int | None = None

    notes: str | None = None
    annotation_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProgressRead(BaseModel):
    """
    Progress summary for one annotator.
    """

    annotator_id: str
    assigned_total: int
    annotated_total: int
    remaining_total: int