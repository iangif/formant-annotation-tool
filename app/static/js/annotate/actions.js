import { state } from "./state.js";
import { setControlsEnabled, showToast, flashSaveConfirmation, fadeOutSpectrogram } from "./ui.js";
import { loadNextToken } from "./api.js";
import {
    buildAcceptAutoPayload,
    buildBadTokenPayload,
    buildNeedsCorrectionPayload,
    buildPanelFieldPayload,
} from "./payloads.js";

export async function savePayload(payload) {
    if (!state.currentToken || state.isSaving) {
        return;
    }

    state.isSaving = true;
    setControlsEnabled(false);

    try {
        const response = await fetch("/api/annotations", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            const message = errorData?.detail || "Failed to save annotation.";
            throw new Error(message);
        }

        flashSaveConfirmation();
        await fadeOutSpectrogram();
        await loadNextToken();

    } catch (error) {
        showToast(error.message, "danger");
        setControlsEnabled(true);

    } finally {
        state.isSaving = false;
    }
}

export async function saveAcceptAuto() {
    await savePayload(buildAcceptAutoPayload());
}

export async function saveBadToken() {
    await savePayload(buildBadTokenPayload());
}

export async function saveNeedsCorrection() {
    await savePayload(buildNeedsCorrectionPayload());
}

export async function saveCurrentPanelFields() {
    await savePayload(buildPanelFieldPayload());
}