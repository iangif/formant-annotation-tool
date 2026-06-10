"""
FastTrackPy integration service.

Temporary FastTrack reruns are stored outside app/static and streamed through an API endpoint. They are promoted only if the annotator submits while viewing the alternative spectrogram.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import hashlib
import json
import os

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib
matplotlib.use("Agg", force=True)

from app.config import PROJECT_ROOT, STATIC_DIR
from app.models import Token
from app.schemas import FastTrackRequest

TEMP_FASTTRACK_DIR = Path(tempfile.gettempdir()) / "formant_annotation_tool" / "fasttrack"

FASTTRACK_ENTRY_CLASSES = ["words", "phones", "vowel"]
FASTTRACK_TARGET_TIER = "vowel"
FASTTRACK_TARGET_LABELS = r"\*"

class FastTrackServiceError(RuntimeError):
    """Base error for FastTrack rerun/promotion failures."""

class FastTrackInputFileError(FastTrackServiceError):
    """Raised when a token is missing required source files."""

class FastTrackGenerationError(FastTrackServiceError):
    """Raised when FastTrackPy fails or produces no candidate."""

@dataclass(frozen=True)
class FastTrackGeneratedFiles:
    """
    Files created by a FastTrack rerun.
    """

    image_path: Path
    pickle_path: Path
    image_url: str
    cache_key: str
    auto_winner_panel: int

@dataclass(frozen=True)
class FastTrackPromotedFiles:
    """
    Files promoted from the temporary location to the committed token location.
    """

    image_path_value: str
    candidates_pickle_path_value: str | None

def get_fasttrack_cache_key(params: FastTrackRequest) -> str:
    payload = {
        "min_max_formant": params.min_max_formant,
        "max_max_formant": params.max_max_formant,
        "n_formants": params.n_formants,
    }

    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]

def get_temp_fasttrack_image_path(token_id: str, cache_key: str | None = None) -> Path:
    if cache_key is None:
        return TEMP_FASTTRACK_DIR / f"{token_id}.png"

    return TEMP_FASTTRACK_DIR / f"{token_id}_{cache_key}.png"

def get_temp_fasttrack_pickle_path(token_id: str, cache_key: str | None = None) -> Path:
    if cache_key is None:
        return TEMP_FASTTRACK_DIR / f"{token_id}.pkl"

    return TEMP_FASTTRACK_DIR / f"{token_id}_{cache_key}.pkl"

def _resolve_project_path(path_value: str | None) -> Path | None:
    """
    Converts a stored path into a filesystem path.
    """

    if path_value is None:
        return None

    path_value = path_value.replace("\\", "/")

    if path_value.startswith("/static/"):
        return STATIC_DIR / path_value.removeprefix("/static/")

    if path_value.startswith("static/"):
        return STATIC_DIR / path_value.removeprefix("static/")

    path = Path(path_value)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path

def _require_existing_file(path_value: str | None, label: str) -> Path:
    """
    Resolve and validate a required source file.
    """

    path = _resolve_project_path(path_value)

    if path is None:
        raise FastTrackInputFileError(f"Token is missing {label} path.")

    if not path.exists():
        raise FastTrackInputFileError(f"Could not find {label} file: {path}")

    return path

def generate_fasttrack_alternative(
    *,
    token: Token,
    params: FastTrackRequest,
) -> FastTrackGeneratedFiles:
    """
    Reruns FastTrackPy for one token and creates one temporary alternative.

    Existing temp files for the same token are overwritten.
    The committed image/pickle paths are not touched.
    """

    audio_path = _require_existing_file(token.audio_path, "audio")
    textgrid_path = _require_existing_file(token.textgrid_path, "TextGrid")

    TEMP_FASTTRACK_DIR.mkdir(parents=True, exist_ok=True)

    cache_key = get_fasttrack_cache_key(params)

    temp_image_path = get_temp_fasttrack_image_path(token.token_id, cache_key)
    temp_pickle_path = get_temp_fasttrack_pickle_path(token.token_id, cache_key)

    if temp_image_path.exists() and temp_pickle_path.exists():
        # Regenerate winner metadata cheaply from the cached pickle when possile.
        from fasttrackpy.processors.outputs import unpickle_candidates

        candidates = unpickle_candidates(temp_pickle_path)

        return FastTrackGeneratedFiles(
            image_path=temp_image_path,
            pickle_path=temp_pickle_path,
            image_url=f"/api/tokens/{token.token_id}/fasttrack-image?cache_key={cache_key}",
            cache_key=cache_key,
            auto_winner_panel=int(candidates.winner_idx),
        )

    try:
        from fasttrackpy import process_audio_textgrid
        from fasttrackpy.processors.outputs import pickle_candidates

        all_vowels = process_audio_textgrid(
            audio_path=str(audio_path),
            textgrid_path=str(textgrid_path),
            entry_classes=FASTTRACK_ENTRY_CLASSES,
            target_tier=FASTTRACK_TARGET_TIER,
            target_labels=FASTTRACK_TARGET_LABELS,
            min_max_formant=params.min_max_formant,
            max_max_formant=params.max_max_formant,
            max_number_of_formants=5.5,
            n_formants=params.n_formants,
            nstep=token.n_candidates,
        )

        if not all_vowels:
            raise FastTrackGenerationError("FastTrackPy returned no vowel candidates.")

        if len(all_vowels) != 1:
            raise FastTrackGenerationError("FastTrackPy returned multiple candidates.")

        candidates = all_vowels[0]
        auto_winner_panel = int(candidates.winner_idx)

        candidates.spectrograms(
            formants=params.n_formants,
            maximum_frequency=4800,
            time_step = 0.001,
            file_name=str(temp_image_path),
            dpi=150,
        )

        import matplotlib.pyplot as plt
        plt.close("all")

        pickle_candidates(candidates, str(temp_pickle_path))

    except FastTrackServiceError:
        raise

    except Exception as exc:
        raise FastTrackGenerationError(
            f"FastTrackPy failed for token {token.token_id}: {exc}"
        ) from exc
    
    if not temp_image_path.exists():
        raise FastTrackGenerationError(
            f"FastTrackPy did not create expected image: {temp_image_path}"
        )

    if not temp_pickle_path.exists():
        raise FastTrackGenerationError(
            f"FastTrackPy did not create expected pickle: {temp_pickle_path}"
        )
    
    return FastTrackGeneratedFiles(
        image_path=temp_image_path,
        pickle_path=temp_pickle_path,
        image_url=f"/api/tokens/{token.token_id}/fasttrack-image?cache_key={cache_key}",
        cache_key=cache_key,
        auto_winner_panel=auto_winner_panel,
    )

def promote_fasttrack_alternative(
    *,
    token: Token,
    cache_key: str | None = None,
) -> FastTrackPromotedFiles:
    """
    Copy the temporary FastTrack result over the token's committed files.

    After promotion, the temporary files are deleted.
    """

    temp_image_path = get_temp_fasttrack_image_path(token.token_id, cache_key)
    temp_pickle_path = get_temp_fasttrack_pickle_path(token.token_id, cache_key)

    if not temp_image_path.exists():
        raise FastTrackInputFileError(
            f"No temporary FastTrack spectrogram exists for token {token.token_id}."
        )

    committed_image_path = (
        _resolve_project_path(token.image_path)
        if token.image_path is not None
        else STATIC_DIR / "images" / f"{token.token_id}.png"
    )

    committed_image_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(temp_image_path, committed_image_path)

    committed_pickle_path = (
        _resolve_project_path(token.candidates_pickle_path)
        if token.candidates_pickle_path is not None
        else PROJECT_ROOT / "data" / "pickles" / f"{token.token_id}.pkl"
    )

    committed_pickle_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(temp_pickle_path, committed_pickle_path)

    temp_image_path.unlink(missing_ok=True)
    temp_pickle_path.unlink(missing_ok=True)

    return FastTrackPromotedFiles(
        image_path_value=str(committed_image_path.relative_to(PROJECT_ROOT)),
        candidates_pickle_path_value=str(committed_pickle_path.relative_to(PROJECT_ROOT)),
    )