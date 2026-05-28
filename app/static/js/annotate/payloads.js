import { elements, annotatorId } from "./dom.js";
import { state } from "./state.js";
import { MIN_PANEL, MAX_PANEL } from "./constants.js";
import {
    readAllPanelInputs,
    panelsAreValid,
    hasAtLeastOnePanel,
} from "./panels.js";

/**
 * Builds the base JSON payload
 */
export function buildBasePayload(decision) {
    if (!state.currentToken) {
        throw new Error("No token is currently loaded.");
    }

    const payload = {
        token_id: state.currentToken.id,
        annotator_id: annotatorId,
        decision: decision,
        notes: elements.notes.value.trim() || null,
        image_source: state.displayedImageSource,
        displayed_auto_winner_panel: state.displayedAutoWinnerPanel,
    };

    if (state.displayedImageSource === "alternate") {
        payload.fasttrack_params = state.alternateFastTrackParams;
        payload.fasttrack_cache_key = state.fasttrackCacheKey;
    }

    return payload;
}

export function buildAcceptAutoPayload() {
    return buildBasePayload("accept_auto");
}

export function buildBadTokenPayload() {
    return buildBasePayload("bad_token");
}


export function buildNeedsCorrectionPayload() {
    return buildBasePayload("needs_correction");
}

/**
 * Builds the JSON payload based on panel inputs.
 */
export function buildPanelFieldPayload() {
    const panels = readAllPanelInputs();
    
    if (!panelsAreValid(panels)) {
        throw new Error(`F1-F4 panel values must be blank or integers from ${MIN_PANEL} to ${MAX_PANEL}.`);
    }

    if (!hasAtLeastOnePanel(panels)) {
        throw new Error("At least one F1-F4 panel value is required.");
    }

    const [panelF1, panelF2, panelF3, panelF4] = panels;
    const autoWinner = state.displayedAutoWinnerPanel;

    const allFilled = panels.every((panel) => panel !== null);
    const nonNullPanels = panels.filter((panel) => panel !== null);
    const uniqueNonNullPanels = new Set(nonNullPanels);

    if (allFilled && panels.every((panel) => panel === autoWinner)) {
        return buildBasePayload("accept_auto");
    }

    if (allFilled && uniqueNonNullPanels.size === 1) {
        const selectedPanel = panelF1;

        return {
            ...buildBasePayload("select_panel"),
            selected_panel: selectedPanel,
            panel_f1: selectedPanel,
            panel_f2: selectedPanel,
            panel_f3: selectedPanel,
            panel_f4: selectedPanel,
        };
    }

    return {
        ...buildBasePayload("complex"),
        panel_f1: panelF1,
        panel_f2: panelF2,
        panel_f3: panelF3,
        panel_f4: panelF4,
    }
}