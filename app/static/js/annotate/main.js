import { elements } from "./dom.js";
import { state } from "./state.js";
import { showToast, setControlsEnabled } from "./ui.js";
import { loadNextToken, openCurrentTokenInPraat, closePraat } from "./api.js";
import { registerSpectrogramEvents } from "./spectrogram.js";
import { registerKeyboardShortcuts } from "./keyboard.js";
import {
    restoreRightPanelWidth,
    registerResizeHandle,
} from "./resize-panel.js";
import { registerFastTrackEvents } from "./fasttrack.js";
import { registerPanelInputEvents } from "./panels.js";

function registerButtonEvents() {
    elements.reloadTokenBtn.addEventListener("click", async () => {
        try {
            await loadNextToken();
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.openPraatBtn.addEventListener("click", async () => {
        elements.openPraatBtn.disabled = true;

        try {
            const result = await openCurrentTokenInPraat();
            showToast(result.message || "Opened token in Praat.", "success");

        } catch (error) {
            showToast(error.message, "danger");

        } finally {
            elements.openPraatBtn.disabled = !state.currentToken;
        }
    });

    elements.closePraatBtn.addEventListener("click", async () => {
        elements.closePraatBtn.disabled = true;

        try {
            const result = await closePraat();

            if(!result.closed) {
                showToast(result.message || "No app-opened Praat process is currently running.", "info");
            }

        } catch (error) {
            showToast(error.message, "danger");

        } finally {
            elements.closePraatBtn.disabled = false;
        }
    });
}

async function main() {
    registerButtonEvents();
    registerFastTrackEvents();
    registerPanelInputEvents();
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