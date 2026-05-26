import { elements, annotatorId } from "./dom.js";
import { state } from "./state.js";
import { setControlsEnabled } from "./ui.js";
import { hidePanelHoverOverlay } from "./spectrogram.js";
import { renderToken, renderNoTokensRemaining } from "./render.js";

export function formatApiError(data, fallbackMessage) {
    if (!data) {
        return fallbackMessage;
    }

    if (typeof data.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data.detail)) {
        return data.detail
            .map((error) => {
                const field = error.loc?.slice(1).join(".");
                const message = error.msg || "Invalid value.";

                return field ? `${field}: ${message}` : message;
            })
            .join(" ");
    }

    if (typeof data.detail === "object") {
        return JSON.stringify(data.detail);
    }

    return fallbackMessage;
}

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

/**
 * Ask the backend to open the current token in Praat.
 */
export async function openCurrentTokenInPraat() {
    if (!state.currentToken) {
        throw new Error("No token is currently loaded.");
    }

    const response = await fetch(`/api/tokens/${encodeURIComponent(state.currentToken.id)}/open-praat`, {
        method: "POST",
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const message = data?.detail || "Failed to open token in Praat.";
        throw new Error(message);
    }

    return data;
}

/**
 * Ask the backend to close the Praat process opened by this app.
 */
export async function closePraat() {
    const response = await fetch("/api/praat/close", {
        method: "POST",
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const message = data?.detail || "Failed to close Praat.";
        throw new Error(message);
    }

    return data;
}