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
            Number.isInteger(panel) &&
            panel >= MIN_PANEL &&
            panel <= MAX_PANEL
    );
}

/**
 * Sets all panels given a panel number.
 */
export function setAllPanelInputs(panelNumber) {
    elements.panelF1.value = panelNumber;
    elements.panelF2.value = panelNumber;
    elements.panelF3.value = panelNumber;
    elements.panelF4.value = panelNumber;
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