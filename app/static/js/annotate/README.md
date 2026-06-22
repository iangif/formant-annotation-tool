# Annotate JavaScript Modules

This folder contains the frontend logic for the annotation page. The app uses vanilla JavaScript ES modules. Each file is organized by responsibility.

## Entry Point

`main.js` is the only file loaded directly by `annotate.html`.

It initializes the page by:

1. registering button events
2. registering spectrogram mouse events
3. registering keyboard shortcuts
4. restoring the right-panel width
5. loading the first available token

## Main Flow

Typical annotation flow:

1. `main.js` starts the page.
2. `api.js` loads the next token from the backend.
3. `render.js` displays token metadata and the spectrogram.
4. The user interacts through keyboard shortcuts, buttons, or the spectrogram.
5. `payloads.js` builds the annotation payload.
6. `actions.js` saves the annotation.
7. `api.js` loads the next token.

## File Responsibilities

- `constants.js`: Shared constants such as panel counts, valid panel range, grid offsets, and resize limits.
- `state.js`: Shared mutable frontend state, including the current token, save status, and hovered panel.
- `dom.js`: Cached DOM references and the current annotator ID.
- `utils.js`: Small general-purpose helpers, such as `sleep`, `clamp`, and display fallbacks.
- `api.js`: Backend communication for loading progress and loading the next token.
- `render.js`: Updates the page when a token loads or when no tokens remain.
- `ui.js`: UI helpers such as toasts, spectrogram fade transitions, save confirmation flashes, and enabling/disabling controls.
- `panels.js`: Reads, validates, and updates the F1-F4 panel input fields.
- `payloads.js`: Builds JSON payloads for annotation submissions.
- `notes.js`: Saves mutable token notes, renders note cues/dropdown, and handles note focus/blur behavior.
- `actions.js`: Coordinates save actions, posts annotations to the backend, handles success/error behavior, and loads the next token.
- `spectrogram.js`: Handles image sizing, hover overlay, panel detection, click selection, and shift-click save.
- `keyboard.js`: Handles keyboard shortcuts.
- `resize-panel.js`: Handles draggable right-panel resizing and localStorage persistence.