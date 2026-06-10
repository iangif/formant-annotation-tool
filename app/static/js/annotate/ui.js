import { elements } from "./dom.js";
import { state } from "./state.js";
import { sleep } from "./utils.js";

/**
 * Show toast message.
 */
export function showToast(message, type = "danger") {
    const fragment = elements.toastTemplate.content.cloneNode(true);

    const toastElement = fragment.querySelector(".toast");
    const toastBody = fragment.querySelector(".toast-body");

    toastElement.classList.add(`text-bg-${type}`);
    toastBody.textContent = message;

    elements.toastContainer.appendChild(fragment);

    const mountedToast = elements.toastContainer.lastElementChild;

    const toast = new bootstrap.Toast(mountedToast, {
        autohide: type !== "danger",
        delay: 2500,
    });

    mountedToast.addEventListener("hidden.bs.toast", () => {
        mountedToast.remove();
    });

    toast.show();
}

/**
 * Called when spectrogram is fading out.
 */
export async function fadeOutSpectrogram(direction = 0) {
    if (elements.spectrogramWrapper.classList.contains("d-none")) {
        return;
    }

    setSpectrogramTransitionDirection(direction);
    elements.spectrogramWrapper.classList.add("is-transitioning");
    await sleep(120);
}

/**
 * Store the direction used by the next spectrogram transition.
 */
export function setSpectrogramTransitionDirection(direction = 0) {
    elements.spectrogramWrapper.classList.remove(
        "transition-left",
        "transition-right"
    );

    if (direction < 0) {
        elements.spectrogramWrapper.classList.add("transition-left");
    } else if (direction > 0) {
        elements.spectrogramWrapper.classList.add("transition-right");
    }
}

/**
 * Called when spectrogram is fading in.
 */
export function fadeInSpectrogram() {
    elements.spectrogramWrapper.classList.remove("is-transitioning");
}

export function openHotkeysPanel() {
    state.hotkeysPanelOpen = true;
    elements.hotkeysBackdrop.classList.remove("d-none");
    elements.hotkeysBackdrop.setAttribute("aria-hidden", "false");
    elements.closeHotkeysBtn.focus();
}

export function closeHotkeysPanel() {
    state.hotkeysPanelOpen = false;
    elements.hotkeysBackdrop.classList.add("d-none");
    elements.hotkeysBackdrop.setAttribute("aria-hidden", "true");
    elements.hotkeysBtn.focus();
}

/**
 * Border flash confirmation after submitting an annotation.
 */
export function flashSaveConfirmation() {
    elements.spectrogramWrapper.classList.remove("save-confirmed");
    void elements.spectrogramWrapper.offsetWidth;
    elements.spectrogramWrapper.classList.add("save-confirmed");

    window.setTimeout(() => {
        elements.spectrogramWrapper.classList.remove("save-confirmed");
    }, 260);
}

/**
 * Enable or disable annotation controls.
 */
export function setControlsEnabled(enabled) {
    const controls = [
        elements.panelF1,
        elements.panelF2,
        elements.panelF3,
        elements.panelF4,
        elements.notes,
        elements.batchMenuBtn,
        elements.jumpTokenBtn,
        elements.autoAdvanceToggle,
        elements.hotkeysBtn,
        elements.reloadTokenBtn,
        elements.openPraatBtn,
        elements.fasttrackMenuBtn,
        elements.fasttrackMinMaxFormant,
        elements.fasttrackMaxMaxFormant,
        elements.fasttrackNFormants,
        elements.restoreOriginalBtn,
    ];

    for (const control of controls) {
        control.disabled = !enabled;
    }
}

export function restoreAutoAdvancePreference() {
    const storedValue = window.localStorage.getItem("formantAutoAdvanceEnabled");
    state.autoAdvanceEnabled = storedValue === null ? true : storedValue === "true";
    elements.autoAdvanceToggle.checked = state.autoAdvanceEnabled;
}

export function persistAutoAdvancePreference() {
    state.autoAdvanceEnabled = elements.autoAdvanceToggle.checked;
    window.localStorage.setItem(
        "formantAutoAdvanceEnabled",
        String(state.autoAdvanceEnabled)
    );
}
