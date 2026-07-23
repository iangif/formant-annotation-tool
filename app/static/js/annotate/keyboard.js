import {
    saveAcceptAuto,
    saveBadToken,
    saveCurrentPanelFields,
} from "./actions.js";
import { loadAdjacentToken } from "./api.js";
import { state } from "./state.js";
import { closeHotkeysPanel, showToast } from "./ui.js";
import { elements } from "./dom.js";

/**
 * Ignore hotkeys while the user is typing into form fields.
 * Enter remains handled before this check so formant fields can submit quickly.
 */
export function isTypingInInput(event) {
    const tagName = event.target.tagName.toLowerCase();

    return tagName === "input" || tagName === "textarea" || tagName === "select";
}

const formantControls = [
    { input: elements.panelF1, checkbox: elements.needsCorrectionF1 },
    { input: elements.panelF2, checkbox: elements.needsCorrectionF2 },
    { input: elements.panelF3, checkbox: elements.needsCorrectionF3 },
    { input: elements.panelF4, checkbox: elements.needsCorrectionF4 },
];

function focusedFormantControl() {
    return formantControls.find(
        ({ input, checkbox }) =>
            document.activeElement === input || document.activeElement === checkbox
    );
}

function focusFormant(formantNumber) {
    formantControls[formantNumber - 1].input.focus();
}

async function runShortcut(callback) {
    try {
        await callback();
    } catch (error) {
        showToast(error.message, "danger");
    }
}

export function registerKeyboardShortcuts() {
    document.addEventListener("keydown", (event) => {
        if (state.hotkeysPanelOpen) {
            if (event.key === "Escape") {
                event.preventDefault();
                closeHotkeysPanel();
            }
            return;
        }

        if (event.key === "Enter") {
            if (event.target === elements.notes) {
                return; // allow newline in notes textarea
            }

            event.preventDefault();
            runShortcut(saveCurrentPanelFields);
            return;
        }

        const focusedFormant = focusedFormantControl();
        if (event.key === "Escape" && focusedFormant) {
            event.preventDefault();
            document.activeElement.blur();
            return;
        }

        if (event.key.toLowerCase() === "x") {
            if (focusedFormant) {
                event.preventDefault();
                focusedFormant.checkbox.checked = !focusedFormant.checkbox.checked;
                return;
            }
            if (!isTypingInInput(event)) {
                event.preventDefault();
                showToast("Focus an F1-F4 panel field before pressing X.", "warning");
            }
            return;
        }

        if (isTypingInInput(event)) {
            return;
        }

        if (["1", "2", "3", "4"].includes(event.key)) {
            event.preventDefault();
            focusFormant(Number.parseInt(event.key, 10));
            return;
        }

        if (event.key.toLowerCase() === "n") {
            event.preventDefault();
            document.getElementById("notes")?.focus();
            return;
        }

        if (event.key === "ArrowRight") {
            event.preventDefault();
            runShortcut(() => loadAdjacentToken(1));
            return;
        }

        if (event.key === "ArrowLeft") {
            event.preventDefault();
            runShortcut(() => loadAdjacentToken(-1));
            return;
        }

        if (event.code === "Space") {
            event.preventDefault();
            runShortcut(saveAcceptAuto);
            return;
        }

        if (event.key.toLowerCase() === "b") {
            event.preventDefault();
            runShortcut(saveBadToken);
            return;
        }

    });
}
