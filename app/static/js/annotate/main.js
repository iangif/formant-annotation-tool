import { elements } from "./dom.js";
import { state } from "./state.js";
import {
    closeHotkeysPanel,
    openHotkeysPanel,
    persistAutoAdvancePreference,
    restoreAutoAdvancePreference,
    showToast,
    setControlsEnabled,
} from "./ui.js";
import {
    initializeBatches,
    openBatch,
    openCurrentTokenInPraat,
    closePraat,
    jumpToNextUnannotatedToken,
    reloadCurrentToken,
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

    elements.jumpTokenBtn.addEventListener("click", async () => {
        try {
            await jumpToNextUnannotatedToken();
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.autoAdvanceToggle.addEventListener("change", () => {
        persistAutoAdvancePreference();
    });

    elements.hotkeysBtn.addEventListener("click", openHotkeysPanel);

    elements.closeHotkeysBtn.addEventListener("click", closeHotkeysPanel);

    elements.hotkeysBackdrop.addEventListener("click", (event) => {
        if (event.target === elements.hotkeysBackdrop) {
            closeHotkeysPanel();
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
    restoreAutoAdvancePreference();
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
