"""Pydantic models for adjudication comparison and unsaved draft previews."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConflictBatchRead(BaseModel):
    corpus: str
    batch: str
    conflict_count: int


class ConflictSummaryRead(BaseModel):
    token_id: str
    corpus: str
    batch: str
    batch_index: int
    file_stem: str
    phone: str | None = None
    ipa: str | None = None
    word: str | None = None
    annotator_count: int


class ConflictAnnotationRead(BaseModel):
    annotator_id: str
    decision: str
    selected_panel: int | None = None
    panel_f1: int | None = None
    panel_f2: int | None = None
    panel_f3: int | None = None
    panel_f4: int | None = None
    needs_correction_f1: bool
    needs_correction_f2: bool
    needs_correction_f3: bool
    needs_correction_f4: bool
    annotation_version: str | None = None
    created_at: str | None = None
    note: str = ""


class ConflictDetailRead(BaseModel):
    token_id: str
    corpus: str
    batch: str
    batch_index: int
    file_stem: str
    speaker: str | None = None
    gender: str | None = None
    discourse: str | None = None
    phone: str | None = None
    ipa: str | None = None
    syllable: str | None = None
    word: str | None = None
    transcription: str | None = None
    previous_phone: str | None = None
    previous_phone_ipa: str | None = None
    following_phone: str | None = None
    following_phone_ipa: str | None = None
    phone_begin: float | None = None
    phone_end: float | None = None
    phone_begin_corrected: float | None = None
    phone_end_corrected: float | None = None
    auto_winner_panel: int | None = None
    n_candidates: int | None = None
    max_plotting_frequency: float | None = None
    image_url: str | None = None
    audio_url: str | None = None
    track_preview_available: bool
    annotations: list[ConflictAnnotationRead]


class DraftTrackPreviewRequest(BaseModel):
    """Panel choices sent only for rendering; this model is never persisted."""

    token_id: str = Field(min_length=1)
    panel_f1: int | None = Field(default=None, ge=0)
    panel_f2: int | None = Field(default=None, ge=0)
    panel_f3: int | None = Field(default=None, ge=0)
    panel_f4: int | None = Field(default=None, ge=0)
    needs_correction_f1: bool = False
    needs_correction_f2: bool = False
    needs_correction_f3: bool = False
    needs_correction_f4: bool = False
