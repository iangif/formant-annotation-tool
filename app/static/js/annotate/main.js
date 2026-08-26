import { elements } from "./dom.js";
import { state } from "./state.js";
import { DEMO_BATCH, DEMO_CORPUS } from "./constants.js";
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
    refreshBatches,
    openBatch,
    openCurrentTokenInPraat,
    closePraat,
    jumpToNextUnannotatedToken,
    reloadCurrentToken,
    loadTokenFromBatchIndexInput,
} from "./api.js";
import { registerSpectrogramEvents } from "./spectrogram.js";
import { registerKeyboardShortcuts } from "./keyboard.js";
import {
    restoreRightPanelWidth,
    registerResizeHandle,
} from "./resize-panel.js";
import { registerFastTrackEvents } from "./fasttrack.js";
import { registerPanelInputEvents } from "./panels.js";
import { registerNoteEvents } from "./notes.js";

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

    elements.demoBatchBtn.addEventListener("click", async () => {
        elements.demoBatchBtn.disabled = true;

        try {
            await refreshBatches();
            const demoBatch = state.batches.find(
                (batch) => batch.corpus === DEMO_CORPUS && batch.name === DEMO_BATCH
            );

            if (!demoBatch) {
                throw new Error(
                    "Demo data is not registered. Ensure data/corpora/demo is present and restart the app."
                );
            }

            await openBatch(demoBatch.id);
        } catch (error) {
            showToast(error.message, "danger");
        } finally {
            elements.demoBatchBtn.disabled = false;
        }
    });

    elements.jumpTokenBtn.addEventListener("click", async () => {
        try {
            await jumpToNextUnannotatedToken();
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.batchIndexInput.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter") {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        try {
            await loadTokenFromBatchIndexInput();
        } catch (error) {
            showToast(error.message, "danger");
        } finally {
            elements.batchIndexInput.value = "";
        }
    });

    elements.batchIndexInput.addEventListener("blur", () => {
        elements.batchIndexInput.value = "";
    });

    elements.autoAdvanceToggle.addEventListener("change", () => {
        persistAutoAdvancePreference();
        elements.autoAdvanceToggle.blur();
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

function registerTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((element) => {
        new bootstrap.Tooltip(element, {
            delay: {
                show: 800,
                hide: 0,
            },
        });
    });
}

async function main() {
    restoreAutoAdvancePreference();
    registerButtonEvents();
    registerFastTrackEvents();
    registerPanelInputEvents();
    registerNoteEvents();
    registerSpectrogramEvents();
    registerKeyboardShortcuts();

    restoreRightPanelWidth();
    registerResizeHandle();

    registerTooltips();

    try {
        await initializeBatches();
    } catch (error) {
        showToast(error.message, "danger");
        setControlsEnabled(false);
    }
}

main();
