import { elements } from "./dom.js";
import {
    MIN_RIGHT_PANEL_WIDTH,
    MAX_RIGHT_PANEL_WIDTH,
} from "./constants.js";
import { clamp } from "./utils.js";
import { hidePanelHoverOverlay } from "./spectrogram.js";

/**
 * Sets the width of the right panel, saving the size to local storage.
 */
export function setRightPanelWidth(width) {
    const clampedWidth = clamp(
        width,
        MIN_RIGHT_PANEL_WIDTH,
        MAX_RIGHT_PANEL_WIDTH
    );

    elements.mainLayout.style.setProperty(
        "--right-panel-width",
        `${clampedWidth}px`
    );

    localStorage.setItem("rightPanelWidth", String(clampedWidth));
}

/**
 * Restores width of the right panel from local storage.
 */
export function restoreRightPanelWidth() {
    const savedWidth = Number.parseInt(
        localStorage.getItem("rightPanelWidth"),
        10
    );

    if (Number.isInteger(savedWidth)) {
        setRightPanelWidth(savedWidth);
    }
}

export function registerResizeHandle() {
    let isDragging = false;

    elements.resizeHandle.addEventListener("mousedown", (event) => {
        isDragging = true;
        elements.resizeHandle.classList.add("is-dragging");
        document.body.style.cursor = "col-resize";
        event.preventDefault();
    });

    document.addEventListener("mousemove", (event) => {
        if (!isDragging) {
            return;
        }

        const layoutRect = elements.mainLayout.getBoundingClientRect();

        /*
            Right panel width is distance from mouse to right edge
            of the full layout.
        */
        const newWidth = layoutRect.right - event.clientX;

        setRightPanelWidth(newWidth);
        hidePanelHoverOverlay();
    });

    document.addEventListener("mouseup", () => {
        if (!isDragging) {
            return;
        }

        isDragging = false;
        elements.resizeHandle.classList.remove("is-dragging");
        document.body.style.cursor = "";
    });
}