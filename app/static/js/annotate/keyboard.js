import {
    saveAcceptAuto,
    saveBadToken,
    saveNeedsCorrection,
    saveCurrentPanelFields,
} from "./actions.js";
import { loadAdjacentToken } from "./api.js";
import { state } from "./state.js";
import { closeHotkeysPanel, showToast } from "./ui.js";

/**
 * Ignore hotkeys while the user is typing into form fields.
 * Enter remains handled before this check so formant fields can submit quickly.
 */
export function isTypingInInput(event) {
    const tagName = event.target.tagName.toLowerCase();

    return tagName === "input" || tagName === "textarea" || tagName === "select";
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
            event.preventDefault();
            runShortcut(saveCurrentPanelFields);
            return;
        }

        if (isTypingInInput(event)) {
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

        if (event.key.toLowerCase() === "x") {
            event.preventDefault();
            runShortcut(saveNeedsCorrection);
        }
    });
}
