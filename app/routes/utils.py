from app.models import Token
from app.schemas import AnnotationRead, BatchTokenRead, TokenRead

def token_to_read(token: Token) -> TokenRead:
    return TokenRead(
        id=token.id,
        corpus=token.corpus.name,
        speaker_id=token.speaker_id,
        vowel_label=token.vowel_label,
        word=token.word,
        preceding_phone=token.preceding_phone,
        following_phone=token.following_phone,
        duration_ms=token.duration_ms,
        min_max_formant=token.min_max_formant,
        max_max_formant=token.max_max_formant,
        n_formants=token.n_formants,
        n_candidates=token.n_candidates,
        auto_winner_panel=token.auto_winner_panel,
        image_url=f"/api/files/tokens/{token.id}/image",
        audio_url=f"/api/files/tokens/{token.id}/audio" if token.audio_path else None,
        textgrid_url=f"/api/files/tokens/{token.id}/textgrid" if token.textgrid_path else None,
    )

def token_to_batch_read(token: Token, latest_annotation) -> BatchTokenRead:
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
        is_annotated=latest_annotation is not None,
    )