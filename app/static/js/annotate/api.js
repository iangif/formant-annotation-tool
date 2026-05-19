import { elements, annotatorId } from "./dom.js";
import { state } from "./state.js";
import { setControlsEnabled } from "./ui.js";
import { hidePanelHoverOverlay } from "./spectrogram.js";
import { renderToken, renderNoTokensRemaining } from "./render.js";

/**
 * Load and display annotation progress.
 */
export async function loadProgress() {
    const response = await fetch(`/api/progress?annotator_id=${encodeURIComponent(annotatorId)}`);

    if (!response.ok) {
        throw new Error("Failed to load progress.");
    }

    const progress = await response.json();

    elements.progressLabel.textContent =
        `${progress.annotated_total} / ${progress.assigned_total} annotated ` +
        `(${progress.remaining_total} remaining)`;
}

/**
 * Load the next available token for this annotator.
 */
export async function loadNextToken() {
    setControlsEnabled(false);
    hidePanelHoverOverlay();

    elements.emptyState.classList.remove("d-none");
    elements.emptyState.textContent = "Loading next token...";
    elements.spectrogramWrapper.classList.add("d-none");

    const response = await fetch(`/api/tokens/next?annotator_id=${encodeURIComponent(annotatorId)}`);

    if (!response.ok) {
        throw new Error("Failed to load next token.");
    }

    const token = await response.json();

    if (token === null) {
        state.currentToken = null;
        renderNoTokensRemaining();
        await loadProgress();
        return;
    }

    state.currentToken = token;
    renderToken(token);
    setControlsEnabled(true);
    await loadProgress();
}