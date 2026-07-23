import { elements } from "./dom.js";
import { MIN_PANEL, MAX_PANEL } from "./constants.js";

/**
 * Read a panel input as an integer or null.
 */
export function readPanelInput(inputElement) {
    const value = inputElement.value.trim();

    if (value === "") {
        return null;
    }

    if (!/^\d+$/.test(value)) {
        return Number.NaN;
    }

    return Number.parseInt(value, 10);
}

/**
 * Read all panel inputs as a list of integer or null.
 */
export function readAllPanelInputs() {
    return [
        readPanelInput(elements.panelF1),
        readPanelInput(elements.panelF2),
        readPanelInput(elements.panelF3),
        readPanelInput(elements.panelF4),
    ];
}

/**
 * Returns whether all panels are valid.
 */
export function panelsAreValid(panels) {
    return panels.every(
        (panel) =>
            panel === null ||
            (
                Number.isInteger(panel) &&
                panel >= MIN_PANEL &&
                panel <= MAX_PANEL
            )
    );
}

export function hasAtLeastOnePanel(panels) {
    return panels.some((panel) => panel !== null);
}

export function readNeedsCorrectionFlags() {
    return {
        needs_correction_f1: elements.needsCorrectionF1.checked,
        needs_correction_f2: elements.needsCorrectionF2.checked,
        needs_correction_f3: elements.needsCorrectionF3.checked,
        needs_correction_f4: elements.needsCorrectionF4.checked,
    };
}

export function setNeedsCorrectionFlagsFromAnnotation(annotation = {}) {
    elements.needsCorrectionF1.checked = Boolean(annotation.needs_correction_f1);
    elements.needsCorrectionF2.checked = Boolean(annotation.needs_correction_f2);
    elements.needsCorrectionF3.checked = Boolean(annotation.needs_correction_f3);
    elements.needsCorrectionF4.checked = Boolean(annotation.needs_correction_f4);
}

export function annotationHasNeedsCorrection(annotation = {}) {
    return [1, 2, 3, 4].some(
        (formant) => Boolean(annotation[`needs_correction_f${formant}`])
    );
}

/**
 * Sets all panels given a panel number.
 */
export function setAllPanelInputs(panelNumber) {
    elements.panelF1.value = panelNumber ?? "";
    elements.panelF2.value = panelNumber ?? "";
    elements.panelF3.value = panelNumber ?? "";
    elements.panelF4.value = panelNumber ?? "";
}


/**
 * Prefill F1-F4 panel inputs from the latest annotation row.
 * Falls back to selected_panel when the annotation represents one panel for all formants.
 */
export function setPanelInputsFromAnnotation(annotation) {
    const fallbackPanel = annotation.selected_panel ?? "";

    elements.panelF1.value = annotation.panel_f1 ?? fallbackPanel;
    elements.panelF2.value = annotation.panel_f2 ?? fallbackPanel;
    elements.panelF3.value = annotation.panel_f3 ?? fallbackPanel;
    elements.panelF4.value = annotation.panel_f4 ?? fallbackPanel;
    setNeedsCorrectionFlagsFromAnnotation(annotation);
}

/**
 * Briefly flashes the F1-F4 inputs after panel selection.
 */
export function flashPanelInputs() {
    const inputs = [
        elements.panelF1,
        elements.panelF2,
        elements.panelF3,
        elements.panelF4,
    ];

    for (const input of inputs) {
        input.classList.remove("selection-flash");
        void input.offsetWidth;
        input.classList.add("selection-flash");
    }

    window.setTimeout(() => {
        for (const input of inputs) {
            input.classList.remove("selection-flash");
        }
    }, 160);
}

export function registerPanelInputEvents() {
    const inputs = [
        elements.panelF1,
        elements.panelF2,
        elements.panelF3,
        elements.panelF4,
    ];

    for (const input of inputs) {
        input.addEventListener("focus", () => {
            input.select();
        });
    }
}
