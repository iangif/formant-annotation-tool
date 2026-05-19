import { elements } from "./dom.js";
import { state } from "./state.js";
import {
    PANEL_COLUMNS,
    PANEL_ROWS,
    GRID_OFFSET,
} from "./constants.js";
import {
    setAllPanelInputs,
    flashPanelInputs,
} from "./panels.js";
import { saveCurrentPanelFields } from "./actions.js";

/**
 * Match the wrapper aspect ratio to the loaded image.
 *
 * This ensures:
 * - the wrapper dimensions match the real image dimensions
 * - hover overlays stay aligned
 * - different image sizes/aspect ratios work automatically
 */
export function updateSpectrogramAspectRatio() {
    const image = elements.spectrogramImage;

    if (!image.naturalWidth || !image.naturalHeight) {
        return;
    }

    elements.spectrogramWrapper.style.aspectRatio =
        `${image.naturalWidth} / ${image.naturalHeight}`;
}

/**
 * Return the panel-grid rectangle inside the rendered image.
 *
 * The browser gives us the displayed image size with getBoundingClientRect().
 * We then remove proportional margins used by axis labels/ticks.
 */
export function getGridRect() {
    const imageRect = elements.spectrogramImage.getBoundingClientRect();

    const leftInset = imageRect.width * GRID_OFFSET.left;
    const rightInset = imageRect.width * GRID_OFFSET.right;
    const topInset = imageRect.height * GRID_OFFSET.top;
    const bottomInset = imageRect.height * GRID_OFFSET.bottom;

    return {
        imageRect: imageRect,
        left: imageRect.left + leftInset,
        top: imageRect.top + topInset,
        width: imageRect.width - leftInset - rightInset,
        height: imageRect.height - topInset - bottomInset,
        leftInset: leftInset,
        topInset: topInset,
    };
}

/**
 * Hides panel hover overlay.
 */
export function hidePanelHoverOverlay() {
    state.hoveredPanel = null;
    elements.panelHoverOverlay.classList.add("d-none");
}

/**
 * Converts mouse position to panel index assuming indices go
 * left-to-right then top-to-bottom.
 */
export function getPanelFromMouseEvent(event) {
    const gridRect = getGridRect();

    const x = event.clientX - gridRect.left;
    const y = event.clientY - gridRect.top;

    if (x < 0 || y < 0 || x > gridRect.width || y > gridRect.height) {
        return null;
    }

    const column = Math.min(
        PANEL_COLUMNS - 1,
        Math.floor((x / gridRect.width) * PANEL_COLUMNS)
    );

    const row = Math.min(
        PANEL_ROWS - 1,
        Math.floor((y / gridRect.height) * PANEL_ROWS)
    );

    return row * PANEL_COLUMNS + column;
}

/**
 * Updates and shows visual hover overlay given the panel index.
 */
export function updatePanelHoverOverlay(panelNumber) {
    const gridRect = getGridRect();
    const wrapperRect = elements.spectrogramWrapper.getBoundingClientRect();

    const column = panelNumber % PANEL_COLUMNS;
    const row = Math.floor(panelNumber / PANEL_COLUMNS);

    const panelWidth = gridRect.width / PANEL_COLUMNS;
    const panelHeight = gridRect.height / PANEL_ROWS;

    const left = gridRect.left - wrapperRect.left + column * panelWidth;
    const top = gridRect.top - wrapperRect.top + row * panelHeight;

    elements.panelHoverOverlay.style.left = `${left}px`;
    elements.panelHoverOverlay.style.top = `${top}px`;
    elements.panelHoverOverlay.style.width = `${panelWidth}px`;
    elements.panelHoverOverlay.style.height = `${panelHeight}px`;

    elements.panelHoverLabel.textContent = panelNumber;
    elements.panelHoverOverlay.classList.remove("d-none");
}

/**
 * Brief pulse animation confirming panel selection.
 */
function pulsePanelSelection() {
    elements.panelHoverOverlay.classList.remove("selection-pulse");
    void elements.panelHoverOverlay.offsetWidth;
    elements.panelHoverOverlay.classList.add("selection-pulse");

    window.setTimeout(() => {
        elements.panelHoverOverlay.classList.remove("selection-pulse");
    }, 160);
}

/**
 * Handles mouse movement on the spectrogram image.
 */
export function handleSpectrogramMouseMove(event) {
    if (!state.currentToken || state.isSaving) {
        hidePanelHoverOverlay();
        return;
    }

    const panelNumber = getPanelFromMouseEvent(event);

    if (panelNumber === null) {
        hidePanelHoverOverlay();
        return;
    }

    state.hoveredPanel = panelNumber;
    updatePanelHoverOverlay(panelNumber);
}

/**
 * Handles spectrogram click by setting all panels.
 * If shift-click, saves and then immedately submits annotation.
 */
export async function handleSpectrogramClick(event) {
    if (!state.currentToken || state.hoveredPanel === null || state.isSaving) {
        return;
    }

    setAllPanelInputs(state.hoveredPanel);

    pulsePanelSelection();
    flashPanelInputs();

    if (event.shiftKey) {
        await saveCurrentPanelFields();
    }
}

export function registerSpectrogramEvents() {
    elements.spectrogramWrapper.addEventListener(
        "mousemove",
        handleSpectrogramMouseMove
    );

    elements.spectrogramWrapper.addEventListener(
        "mouseleave",
        hidePanelHoverOverlay
    );

    elements.spectrogramWrapper.addEventListener(
        "click",
        handleSpectrogramClick
    );
}