"""
Defines how data is structured in the database (SQLAlchemy tables)
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Corpus(Base):
    __tablename__ = "corpora"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    config_path: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    batches: Mapped[list["Batch"]] = relationship(back_populates="corpus")

class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (UniqueConstraint("corpus_id", "name", name="uq_batches_corpus_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpora.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)

    csv_path: Mapped[str] = mapped_column(String, nullable=False)
    local_root: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    corpus: Mapped[Corpus] = relationship(back_populates="batches")
    tokens: Mapped[list["Token"]] = relationship(back_populates="batch")

class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    token_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpora.id"), index=True, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), index=True, nullable=False)

    # For accessing related files on disk
    file_stem: Mapped[str] = mapped_column(String, index=True, nullable=False)

    # Token metadata
    speaker: Mapped[str | None] = mapped_column(String, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    discourse: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    ipa: Mapped[str | None] = mapped_column(String, nullable=True)
    syllable: Mapped[str | None] = mapped_column(String, nullable=True)
    word: Mapped[str | None] = mapped_column(String, nullable=True)
    transcription: Mapped[str | None] = mapped_column(String, nullable=True)

    previous_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    previous_phone_ipa: Mapped[str | None] = mapped_column(String, nullable=True)
    following_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    following_phone_ipa: Mapped[str | None] = mapped_column(String, nullable=True)

    phone_begin: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    syllable_begin: Mapped[float | None] = mapped_column(Float, nullable=True)
    syllable_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_begin: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    clip_begin: Mapped[float | None] = mapped_column(Float, nullable=True)
    clip_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone_begin_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone_end_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Alignment
    alignment: Mapped[str | None] = mapped_column(String, nullable=True)
    alignment_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Related file paths
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)
    textgrid_path: Mapped[str | None] = mapped_column(String, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Fasttrack 
    n_candidates: Mapped[int] = mapped_column(Integer, default=20)
    auto_winner_panel: Mapped[int] = mapped_column(Integer, default=0)
    min_max_formant: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_max_formant: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_formants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_number_of_formants: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidates_pickle_path: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    corpus: Mapped[Corpus] = relationship()
    batch: Mapped[Batch] = relationship(back_populates="tokens")

    @property
    def duration_ms(self) -> float | None:
        if self.phone_begin_corrected is None or self.phone_end_corrected is None:
            return None
        return round((self.phone_end_corrected - self.phone_begin_corrected) * 1000, 2)

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

class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("annotator_id", "corpus_id", "batch_id", name="uq_assignments_annotator_corpus_batch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    annotator_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpora.id"), index=True, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)