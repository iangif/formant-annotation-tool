from app.models import Token
from app.schemas import AnnotationRead, BatchTokenRead, TokenNoteRead, TokenRead

def token_to_read(token: Token) -> TokenRead:
    return TokenRead(
        token_id=token.token_id,
        corpus=token.corpus.name,
        speaker=token.speaker,
        gender=token.gender,
        phone=token.phone,
        ipa=token.ipa,
        word=token.word,
        previous_phone=token.previous_phone,
        following_phone=token.following_phone,
        alignment_comment=token.alignment_comment,
        duration_ms=token.duration_ms,
        min_max_formant=token.min_max_formant,
        max_max_formant=token.max_max_formant,
        n_formants=token.n_formants,
        max_plotting_frequency=token.max_plotting_frequency,
        n_candidates=token.n_candidates,
        auto_winner_panel=token.auto_winner_panel,
        image_url=f"/api/files/tokens/{token.token_id}/image",
        audio_url=f"/api/files/tokens/{token.token_id}/audio" if token.audio_path else None,
        textgrid_url=f"/api/files/tokens/{token.token_id}/textgrid" if token.textgrid_path else None,
    )

def token_to_batch_read(token: Token, latest_annotation, latest_note=None) -> BatchTokenRead:
    base = token_to_read(token).model_dump()

    return BatchTokenRead(
        **base,
        batch_id=token.batch_id,
        batch_index=token.batch_index,
        latest_annotation=(
            AnnotationRead.model_validate(latest_annotation)
            if latest_annotation
            else None
        ),
        latest_note=(
            TokenNoteRead.model_validate(latest_note)
            if latest_note
            else None
        ),
        is_annotated=latest_annotation is not None,
        has_note=bool(latest_note and latest_note.note.strip()),
    )
