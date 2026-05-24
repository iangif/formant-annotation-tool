"""
Utilities for opening token audio/TextGrid files in Praat.

The frontend does not launch Praat directly. Instead, it calls a backend endpoint, and this module validates local paths and opens the current token in Praat's GUI.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import PRAAT_PATH, PROJECT_ROOT

class PraatConfigurationError(RuntimeError):
    """Raised when the Praat executable cannot be found or used."""

class PraatFileError(RuntimeError):
    """Raised when the token's wav/TextGrid files are missing."""

def resolve_project_path(path_value: str | None) -> Path | None:
    """
    Resolve a database path into an absolute local filesystem path.
    """
    if path_value is None:
        return None

    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path

def praat_object_name(path: Path) -> str:
    """
    Convert a filename stem into the object name Praat will create.

    Praat replaces periods with underscores when importing files.
    Example:
        my.toke.wav -> Sound my_token
    """

    return path.stem.replace(".", "_")

def find_praat_executable() -> Path:
    """
    Locate the Praat executable.

    Priority:
    1. PRAAT_PATH from .env
    2. praat available on PATH
    3. Common OS-specific install locations
    """

    candidates: list[Path] = []

    # Check .env
    if PRAAT_PATH:
        candidates.append(Path(PRAAT_PATH))

    # Check system PATH variables
    path_from_shell = shutil.which("praat")
    if path_from_shell:
        candidates.append(Path(path_from_shell))

    # OS-specific locations
    system = platform.system()

    if system == "Darwin":
        candidates.append(Path("/Applications/Praat.app/Contents/MacOS/Praat"))

    elif system == "Windows":
        candidates.extend(
            [
                Path(r"C:\Program Files\Praat\Praat.exe"),
                Path(r"C:\Program Files\Praat.exe"),
                Path(r"C:\Program Files (x86)\Praat\Praat.exe"),
            ]
        )

    else:
        candidates.extend(
            [
                Path("/usr/bin/praat"),
                Path("/usr/local/bin/praat"),
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    raise PraatConfigurationError(
        "Praat is not configured. Install Praat, then set PRAAT_PATH in your .env file."
    )

def validate_token_files(audio_path: Path | None, textgrid_path: Path | None) -> tuple[Path, Path]:
    """
    Ensure the token has both required local files.
    """

    if audio_path is None:
        raise PraatFileError("This token does not have an audio_path.")

    if textgrid_path is None:
        raise PraatFileError("This token does not have a textgrid_path.")

    if not audio_path.exists():
        raise PraatFileError(f"Could not find wav file: {audio_path}")

    if not textgrid_path.exists():
        raise PraatFileError(f"Could not find TextGrid file: {textgrid_path}")

    return audio_path, textgrid_path

def write_open_token_script(audio_path: Path, textgrid_path: Path) -> Path:
    """
    Writes a temporary Praat script that opens the Sound and TextGrid together.

    We use --send, not --run, because this script creates a GUI editor window.
    """
    
    sound_name = praat_object_name(audio_path)
    textgrid_name = praat_object_name(textgrid_path)

    script_text = f"""
    Read from file: "{audio_path.as_posix()}"
    Read from file: "{textgrid_path.as_posix()}"
    selectObject: "Sound {sound_name}", "TextGrid {textgrid_name}"
    View & Edit
    """.strip()

    temp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".praat",
        prefix="open_formant_token_",
        encoding="utf-8",
        delete=False,
    )
    
    with temp:
        temp.write(script_text)
        temp.write("\n")

    return Path(temp.name)

def open_token_in_praat(audio_path_value: str | None, textgrid_path_value: str | None) -> None:
    """
    Opens a token's wav and TextGrid in Praat.

    Raises:
        PraatConfigurationError
        PraatFileError
        RuntimeError
    """ 

    praat_executable = find_praat_executable()

    audio_path = resolve_project_path(audio_path_value)
    textgrid_path = resolve_project_path(textgrid_path_value)
    audio_path, textgrid_path = validate_token_files(audio_path, textgrid_path)

    script_path = write_open_token_script(audio_path, textgrid_path)

    try:
        subprocess.Popen(
            [
                str(praat_executable),
                "--new-send",
                str(script_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise PraatConfigurationError(
            f"Could not launch Praat executable: {praat_executable}"
        ) from exc