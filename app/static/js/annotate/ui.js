import { elements } from "./dom.js";
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
export async function fadeOutSpectrogram() {
    if (elements.spectrogramWrapper.classList.contains("d-none")) {
        return;
    }
    elements.spectrogramWrapper.classList.add("is-transitioning");
    await sleep(140);
}

/**
 * Called when spectrogram is fading in.
 */
export function fadeInSpectrogram() {
    elements.spectrogramWrapper.classList.remove("is-transitioning");
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
        elements.previousTokenBtn,
        elements.nextTokenBtn,
        elements.skipTokenBtn,
        elements.reloadTokenBtn,
        elements.openPraatBtn,
        elements.fasttrackMenuBtn,
        elements.fasttrackMinMaxFormant,
        elements.fasttrackMaxMaxFormant,
        elements.fasttrackNFormants,
        elements.generateFasttrackBtn,
        elements.restoreOriginalBtn,
    ];

    for (const control of controls) {
        control.disabled = !enabled;
    }
}