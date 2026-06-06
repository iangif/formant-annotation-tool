import { elements } from "./dom.js";
import { state } from "./state.js";
import { showToast, setControlsEnabled } from "./ui.js";
import {
    initializeBatches,
    openBatch,
    openCurrentTokenInPraat,
    closePraat,
    loadAdjacentToken,
    reloadCurrentToken,
    skipCurrentToken,
} from "./api.js";
import { registerSpectrogramEvents } from "./spectrogram.js";
import { registerKeyboardShortcuts } from "./keyboard.js";
import {
    restoreRightPanelWidth,
    registerResizeHandle,
} from "./resize-panel.js";
import { registerFastTrackEvents } from "./fasttrack.js";
import { registerPanelInputEvents } from "./panels.js";

function registerButtonEvents() {
    elements.batchMenu.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-batch-id]");

        if (!button) {
            return;
        }

        try {
            await openBatch(Number.parseInt(button.dataset.batchId, 10));
        } catch (error) {
            showToast(error.message, "danger");
            setControlsEnabled(false);
        }
    });

    elements.previousTokenBtn.addEventListener("click", async () => {
        try {
            await loadAdjacentToken(-1);
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.nextTokenBtn.addEventListener("click", async () => {
        try {
            await loadAdjacentToken(1);
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.skipTokenBtn.addEventListener("click", async () => {
        try {
            await skipCurrentToken();
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.reloadTokenBtn.addEventListener("click", async () => {
        try {
            await reloadCurrentToken();
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
        await initializeBatches();
    } catch (error) {
        showToast(error.message, "danger");
        setControlsEnabled(false);
    }
}

main();
