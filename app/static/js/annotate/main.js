import { elements } from "./dom.js";
import { showToast, setControlsEnabled } from "./ui.js";
import { loadNextToken } from "./api.js";
import { registerSpectrogramEvents } from "./spectrogram.js";
import { registerKeyboardShortcuts } from "./keyboard.js";
import {
    restoreRightPanelWidth,
    registerResizeHandle,
} from "./resize-panel.js";

function registerButtonEvents() {
    elements.reloadTokenBtn.addEventListener("click", async () => {
        try {
            await loadNextToken();
        } catch (error) {
            showToast(error.message, "danger");
        }
    });
}

async function main() {
    registerButtonEvents();
    registerSpectrogramEvents();
    registerKeyboardShortcuts();

    restoreRightPanelWidth();
    registerResizeHandle();

    try {
        await loadNextToken();
    } catch (error) {
        showToast(error.message, "danger");
        setControlsEnabled(false);
    }
}

main();