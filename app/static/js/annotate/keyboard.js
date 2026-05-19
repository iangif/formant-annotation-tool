import {
    saveAcceptAuto,
    saveBadToken,
    saveNeedsCorrection,
    saveCurrentPanelFields,
} from "./actions.js";

/**
 * Ignore hotkeys while the user is typing into form fields.
 */
export function isTypingInInput(event) {
    const tagName = event.target.tagName.toLowerCase();

    return tagName === "input" || tagName === "textarea" || tagName === "select";
}

export function registerKeyboardShortcuts() {
    document.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            saveCurrentPanelFields();
            return;
        }

        if (isTypingInInput(event)) {
            return;
        }

        if (event.code === "Space") {
            event.preventDefault();
            saveAcceptAuto();
            return;
        }

        if (event.key.toLowerCase() === "b") {
            event.preventDefault();
            saveBadToken();
            return;
        }

        if (event.key.toLowerCase() === "x") {
            event.preventDefault();
            saveNeedsCorrection();
            return;
        }
    });
}