"""
Defines Pydantic request/response schemas.

These models define the API contract:
- what the frontend receives
- what the frontend sends
- what the backend validates before writing to database
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator, Field
from app.models import AnnotationDecision
from typing import Literal

MIN_PANEL = 0
MAX_PANEL = 19

class TokenRead(BaseModel):
    """
    Token data returned to the frontend.
    Note: image_url and audio_url are browser URLs, not filesystem paths
    """

    token_id: str
    corpus: str
    speaker: str | None = None
    gender: str | None = None
    phone: str
    ipa: str | None = None
    word: str | None = None
    previous_phone: str | None = None
    following_phone: str | None = None
    alignment_comment: str | None = None
    effective_phone_begin: float | None = None
    effective_phone_end: float | None = None
    duration_ms: float | None = None

    min_max_formant: float | None = None
    max_max_formant: float | None = None
    n_formants: int | None = None
    max_plotting_frequency: float | None = None

    n_candidates: int
    auto_winner_panel: int

    image_url: str
    audio_url: str | None = None
    textgrid_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

class TokenSummaryRead(BaseModel):
    """
    List of tokens for a batch overview.
    """

    token_id: str
    batch_id: int
    batch_index: int
    file_stem: str

    phone: str | None = None
    ipa: str | None = None
    word: str | None = None
    speaker: str | None = None

    is_annotated: bool
    latest_decision: AnnotationDecision | None = None
    has_note: bool = False
    note: str | None = None

class BatchTokenRead(TokenRead):
    """
    Additional information to render one token.
    """

    batch_id: int
    batch_index: int
    latest_annotation: AnnotationRead | None = None
    latest_note: TokenNoteRead | None = None
    is_annotated: bool
    has_note: bool = False

class OpenPraatRead(BaseModel):
    """
    Response returned after the backend asks Praat to open a token.
    """

    token_id: str
    opened: bool
    message: str

class ClosePraatRead(BaseModel):
    """
    Response returned after asking the backend to close app-opened Praat.
    """

    closed: bool
    message: str

ImageSource = Literal["original", "alternate"]

class FastTrackRequest(BaseModel):
    """
    Settings the annotator can change before rerunning FastTrackPy.
    """

    min_max_formant: float = Field(gt=0)
    max_max_formant: float = Field(gt=0)
    n_formants: int = Field(ge=1, le=6)

    @model_validator(mode="after")
    def validate_formant_range(self) -> "FastTrackRequest":
        if self.max_max_formant <= self.min_max_formant:
            raise ValueError("max_max_formant must be greater than min_max_formant")

        return self

class FastTrackRead(BaseModel):
    """
    Response returned after creating an alternative spectrogram.
    """

    token_id: str
    alternate_image_url: str
    auto_winner_panel: int = Field(ge=MIN_PANEL, le=MAX_PANEL)
    cache_key: str
    message: str

class AnnotationCreate(BaseModel):
    """
    Payload sent by the frontend when the annotator makes a decision.
    """

    token_id: str
    annotator_id: str
    decision: AnnotationDecision

    image_source: ImageSource = "original"
    fasttrack_params: FastTrackRequest | None = None
    displayed_auto_winner_panel: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    fasttrack_cache_key: str | None = None

    selected_panel: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f1: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f2: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f3: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)
    panel_f4: int | None = Field(default=None, ge=MIN_PANEL, le=MAX_PANEL)

    needs_correction_f1: bool = False
    needs_correction_f2: bool = False
    needs_correction_f3: bool = False
    needs_correction_f4: bool = False

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

        bad_token:
            panel fields are optional.

        Per-formant needs-correction flags are allowed with or without a
        corresponding panel. A flagged formant with no panel remains blank.
        """

        if self.decision == AnnotationDecision.select_panel:
            if self.selected_panel is None:
                raise ValueError("selected_panel is required for select_panel")
        
        if self.decision == AnnotationDecision.complex:
            panels = [self.panel_f1, self.panel_f2, self.panel_f3, self.panel_f4]
            correction_flags = [
                self.needs_correction_f1,
                self.needs_correction_f2,
                self.needs_correction_f3,
                self.needs_correction_f4,
            ]

            if all(panel is None for panel in panels) and not any(correction_flags):
                raise ValueError(
                    "complex requires at least one panel or needs-correction flag"
                )

        if self.decision == AnnotationDecision.needs_correction:
            raise ValueError(
                "needs_correction is a legacy decision. Submit a panel decision "
                "and use needs_correction_f1 through needs_correction_f4 instead."
            )

        if self.image_source == "alternate":
            if self.fasttrack_params is None:
                raise ValueError("fasttrack_params is required for alternate image submissions")

            if self.fasttrack_cache_key is None:
                raise ValueError("fasttrack_cache_key is required for alternate image submissions")

            if self.displayed_auto_winner_panel is None:
                raise ValueError("displayed_auto_winner_panel is required for alternate image submissions")

        return self


class TokenNoteCreate(BaseModel):
    """Payload for creating or replacing the mutable note on one token."""

    token_id: str
    annotator_id: str
    note: str = ""


class TokenNoteRead(BaseModel):
    """Mutable token note returned to the frontend."""

    id: int
    token_id: str
    annotator_id: str
    note: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")

class AnnotationRead(BaseModel):
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

    needs_correction_f1: bool = False
    needs_correction_f2: bool = False
    needs_correction_f3: bool = False
    needs_correction_f4: bool = False

    annotation_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")

class ProgressRead(BaseModel):
    """
    Progress summary for one annotator.
    """

    annotator_id: str
    assigned_total: int
    annotated_total: int
    remaining_total: int

class BatchProgressRead(BaseModel):
    """
    Progress summary for one an annotator's assigned batch.
    """
    id: int
    corpus: str
    name: str
    completed_count: int
    total_count: int
    remaining_count: int
    first_unfinished_index: int | None = None
    is_last_opened: bool = False
