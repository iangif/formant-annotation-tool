import { state } from "./state.js";
import { setControlsEnabled, showToast, flashSaveConfirmation } from "./ui.js";
import {
    closePraat,
    jumpToNextUnannotatedToken,
    refreshBatches,
    updateCurrentBatchTokenSummaryFromLoadedToken,
} from "./api.js";
import {
    buildAcceptAutoPayload,
    buildBadTokenPayload,
    buildNeedsCorrectionPayload,
    buildPanelFieldPayload,
} from "./payloads.js";
import { renderBatchMenu, renderBatchProgress, renderTokenStatus } from "./render.js";

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

        const savedAnnotation = await response.json();
        state.currentToken.latest_annotation = savedAnnotation;
        state.currentToken.is_annotated = true;
        updateCurrentBatchTokenSummaryFromLoadedToken(state.currentToken);
        renderTokenStatus(state.currentToken)

        flashSaveConfirmation();

        try {
            await closePraat();
        } catch (error) {
            showToast(error.message, "warning");
        }

        await refreshBatches();
        renderBatchMenu();
        renderBatchProgress();

        if (state.autoAdvanceEnabled) {
            const didJump = await jumpToNextUnannotatedToken();

            if (!didJump) {
                renderBatchProgress();
                setControlsEnabled(true);
            }
        } else {
            renderBatchProgress();
            setControlsEnabled(true);
        }

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
