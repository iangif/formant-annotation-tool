import { elements, annotatorId } from "./dom.js";
import { state } from "./state.js";
import { fadeOutSpectrogram, setControlsEnabled } from "./ui.js";
import { hidePanelHoverOverlay } from "./spectrogram.js";
import { DEMO_BATCH, DEMO_CORPUS } from "./constants.js";
import {
    renderBatchMenu,
    renderBatchProgress,
    renderNoAssignedBatches,
    renderToken,
} from "./render.js";

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

export async function fetchJson(url, options = {}, fallbackMessage = "Request failed.") {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => null);

    if (!response.ok) {
        throw new Error(formatApiError(data, fallbackMessage));
    }

    return data;
}

export function getCurrentBatchTokenSummary() {
    if (state.currentBatchIndex === null) {
        return null;
    }

    return state.currentBatchTokens.find(
        (token) => token.batch_index === state.currentBatchIndex
    ) || null;
}

export function updateCurrentBatchTokenSummaryFromLoadedToken(token) {
    const summary = getCurrentBatchTokenSummary();

    if (!summary) {
        return;
    }

    if (token.latest_annotation) {
        summary.is_annotated = token.is_annotated;
        summary.latest_decision = token.latest_annotation.decision;
    }

    if (token.latest_note) {
        summary.note = token.latest_note.note;
        summary.has_note = Boolean(token.latest_note.note.trim());
    } else {
        summary.note = null;
        summary.has_note = false;
    }
}

export async function refreshBatches() {
    state.batches = await fetchJson(
        `/api/batches?annotator_id=${encodeURIComponent(annotatorId)}`,
        {},
        "Failed to load batches."
    );

    if (state.currentBatchId !== null) {
        state.currentBatchProgress = state.batches.find(
            (batch) => batch.id === state.currentBatchId
        ) || null;
    }

    renderBatchMenu();
    renderBatchProgress();
    return state.batches;
}

export async function loadBatchTokens(batchId) {
    state.currentBatchTokens = await fetchJson(
        `/api/batches/${encodeURIComponent(batchId)}/tokens?annotator_id=${encodeURIComponent(annotatorId)}`,
        {},
        "Failed to load batch tokens."
    );

    return state.currentBatchTokens;
}

export async function markBatchLastOpened(batchId) {
    await fetchJson(
        `/api/batches/${encodeURIComponent(batchId)}/last-opened?annotator_id=${encodeURIComponent(annotatorId)}`,
        { method: "POST" },
        "Failed to store last-opened batch."
    );
}

export async function loadTokenAtIndex(index, direction = 0) {
    if (state.currentBatchId === null) {
        throw new Error("No batch is currently open.");
    }

    setControlsEnabled(false);
    hidePanelHoverOverlay();
    await fadeOutSpectrogram(direction);

    const token = await fetchJson(
        `/api/batches/${encodeURIComponent(state.currentBatchId)}/tokens/${encodeURIComponent(index)}?annotator_id=${encodeURIComponent(annotatorId)}`,
        {},
        "Failed to load token."
    );

    state.currentToken = token;
    state.currentBatchIndex = token.batch_index;

    renderToken(token);
    setControlsEnabled(true);
}

export async function openBatch(batchId, preferredIndex = null) {
    setControlsEnabled(false);

    state.currentBatchId = batchId;
    state.currentBatchProgress = state.batches.find((batch) => batch.id === batchId) || null;
    state.currentToken = null;
    state.currentBatchIndex = null;


    await markBatchLastOpened(batchId);
    await loadBatchTokens(batchId);

    const startIndex = preferredIndex ?? state.currentBatchProgress?.first_unfinished_index ?? 0;

    renderBatchMenu();
    renderBatchProgress();

    if (state.currentBatchTokens.length === 0) {
        throw new Error("This batch has no tokens.");
    }

    await loadTokenAtIndex(startIndex);
}

export async function initializeBatches() {
    await refreshBatches();

    if (state.batches.length === 0) {
        renderNoAssignedBatches();
        setControlsEnabled(false);
        return;
    }

    const defaultBatch =
        state.batches.find((batch) => batch.is_last_opened) ||
        state.batches.find(
            (batch) => batch.corpus !== DEMO_CORPUS || batch.name !== DEMO_BATCH
        ) ||
        state.batches[0];

    await openBatch(defaultBatch.id);
}

export function getSortedBatchIndices() {
    return state.currentBatchTokens
        .map((token) => token.batch_index)
        .sort((a, b) => a - b);
}

export function getAdjacentBatchIndex(direction) {
    const indices = getSortedBatchIndices();

    if (indices.length === 0 || state.currentBatchIndex === null) {
        return null;
    }

    const position = indices.indexOf(state.currentBatchIndex);

    if (position === -1) {
        return indices[0];
    }

    const nextPosition = position + direction;

    if (nextPosition < 0 || nextPosition >= indices.length) {
        return null;
    }

    return indices[nextPosition];
}

export function getNextUnannotatedIndexAfterCurrent() {
    const indices = getSortedBatchIndices();

    if (indices.length === 0) {
        return null;
    }

    const currentPosition = indices.indexOf(state.currentBatchIndex);
    const safePosition = currentPosition === -1 ? 0 : currentPosition;
    const orderedIndices = [
        ...indices.slice(safePosition + 1),
        ...indices.slice(0, safePosition + 1),
    ];

    return orderedIndices.find((index) => {
        const summary = state.currentBatchTokens.find(
            (token) => token.batch_index === index
        );
        return summary && !summary.is_annotated;
    }) ?? null;
}

function directionFromIndexChange(fromIndex, toIndex) {
    if (fromIndex === null || toIndex === null || fromIndex === toIndex) {
        return 0;
    }

    return toIndex > fromIndex ? 1 : -1;
}

export async function loadAdjacentToken(direction) {
    const nextIndex = getAdjacentBatchIndex(direction);

    if (nextIndex === null) {
        return;
    }

    await loadTokenAtIndex(nextIndex, direction);
}

export async function jumpToNextUnannotatedToken() {
    const nextIndex = getNextUnannotatedIndexAfterCurrent();

    if (nextIndex === null) {
        return false;
    }

    const direction = directionFromIndexChange(state.currentBatchIndex, nextIndex);
    await loadTokenAtIndex(nextIndex, direction);
    return true;
}

export async function loadTokenFromBatchIndexInput() {
    const rawValue = elements.batchIndexInput.value.trim();
    const requestedIndex = Number.parseInt(rawValue, 10);

    if (!Number.isInteger(requestedIndex)) {
        throw new Error("Enter a valid token index.");
    }

    // UI uses 1-based token positions; backend batch_index is 0-based.
    const batchIndex = requestedIndex - 1;

    const exists = state.currentBatchTokens.some(
        (token) => token.batch_index === batchIndex
    );

    if (!exists) {
        throw new Error(`Token index ${requestedIndex} is not in this batch.`);
    }

    const direction = batchIndex > state.currentBatchIndex ? 1 : -1;
    await loadTokenAtIndex(batchIndex, direction);
}

export async function reloadCurrentToken() {
    if (state.currentBatchIndex === null) {
        return;
    }

    await loadTokenAtIndex(state.currentBatchIndex);
}

export async function openCurrentTokenInPraat() {
    if (!state.currentToken) {
        throw new Error("No token is currently loaded.");
    }

    return await fetchJson(
        `/api/tokens/${encodeURIComponent(state.currentToken.token_id)}/open-praat`,
        { method: "POST" },
        "Failed to open token in Praat."
    );
}

export async function closePraat() {
    return await fetchJson(
        "/api/praat/close",
        { method: "POST" },
        "Failed to close Praat."
    );
}
