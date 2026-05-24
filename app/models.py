"""
Defines how data is structured in the database (SQLAlchemy tables)
"""
from datetime import datetime
import enum
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True) # token_id from PolyglotDB
    corpus: Mapped[str] = mapped_column(String, index=True)

    # Token metadata
    speaker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    vowel_label: Mapped[str] = mapped_column(String, index=True)
    word: Mapped[str | None] = mapped_column(String, nullable=True)

    preceding_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    following_phone: Mapped[str | None] = mapped_column(String, nullable=True)

    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Candidate Metadata
    min_max_formant: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_max_formant: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_formants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_number_of_formants: Mapped[float | None] = mapped_column(Float, nullable=True)

    n_candidates: Mapped[int] = mapped_column(Integer, default=20)
    auto_winner_panel: Mapped[int] = mapped_column(Integer)

    # Files
    image_path: Mapped[str] = mapped_column(String)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)
    textgrid_path: Mapped[str | None] = mapped_column(String, nullable=True)
    candidates_pickle_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

"""
Annotation rules:
- accept_auto       -> use token.auto_winner_panel for selected_panel and all panel_f*
- select_panel      -> all panel_f* fields are the same non-winner panel
- complex           -> at least one of the panel_f* differs
- bad_token         -> no panels required
- needs_correction  -> no panels required
"""
class AnnotationDecision(str, enum.Enum):
    accept_auto = "accept_auto"
    select_panel = "select_panel"
    bad_token = "bad_token"
    needs_correction = "needs_correction"
    complex = "complex"

class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(ForeignKey("tokens.id"), index=True, nullable=False)

    annotator_id: Mapped[str] = mapped_column(String, index=True)
    decision: Mapped[AnnotationDecision] = mapped_column(Enum(AnnotationDecision), nullable=False)

    selected_panel: Mapped[int | None] = mapped_column(Integer, nullable=True)

    panel_f1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    panel_f2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    panel_f3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    panel_f4: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotation_version: Mapped[str] = mapped_column(String, default="v1")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TokenAssignment(Base):
    __tablename__ = "token_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[str] = mapped_column(ForeignKey("tokens.id"), index=True)
    annotator_id: Mapped[str] = mapped_column(String, index=True)

    batch_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_overlap: Mapped[bool] = mapped_column(Boolean, default=False)

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )