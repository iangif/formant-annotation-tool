/*

    Frontend logic.

    Responsibilities:
    1. load the next token from the backend
    2. display its spectrogram image and metadata
    3. track hover/click over a 5 x 4 panel image grid
    4. save annotation decisions through the API
    5. load the next token after each save

    Current hotkeys:
    - Space: accept_auto, ignoring F1-F4 fields
    - Enter: save current F1-F4 fields
    - B: mark bad token
    - X: mark needs correction

    Mouse:
    - Hover over spectrogram: highlight panel 0-19
    - Click panel: copy panel number into F1-F4 fields
    - Shift + click panel: copy panel number and save immediately
*/

const PANEL_COLUMNS = 5;
const PANEL_ROWS = 4;
const MIN_PANEL = 0;
const MAX_PANEL = 19;

const MIN_RIGHT_PANEL_WIDTH = 240;
const MAX_RIGHT_PANEL_WIDTH = 700;

const GRID_OFFSET = {
    left: 0.050,
    right: 0.02,
    top: 0.0,
    bottom: 0.05,
}

let currentToken = null;
let isSaving = false;
let hoveredPanel = null;

const annotatorId = document.getElementById("annotator-id").textContent.trim();

const elements = {
    progressLabel: document.getElementById("progress-label"),
    toastContainer: document.getElementById("toast-container"),

    mainLayout: document.getElementById("main-layout"),
    resizeHandle: document.getElementById("resize-handle"),

    emptyState: document.getElementById("empty-state"),
    spectrogramWrapper: document.getElementById("spectrogram-wrapper"),
    spectrogramImage: document.getElementById("spectrogram-image"),
    panelHoverOverlay: document.getElementById("panel-hover-overlay"),
    panelHoverLabel: document.getElementById("panel-hover-label"),

    tokenIdLabel: document.getElementById("token-id-label"),

    metaWord: document.getElementById("meta-word"),
    metaVowel: document.getElementById("meta-vowel"),
    metaCorpus: document.getElementById("meta-corpus"),
    metaSpeaker: document.getElementById("meta-speaker"),
    metaContext: document.getElementById("meta-context"),
    metaDuration: document.getElementById("meta-duration"),
    metaAutoWinner: document.getElementById("meta-auto-winner"),

    audioPlayer: document.getElementById("audio-player"),

    panelF1: document.getElementById("panel-f1"),
    panelF2: document.getElementById("panel-f2"),
    panelF3: document.getElementById("panel-f3"),
    panelF4: document.getElementById("panel-f4"),

    notes: document.getElementById("notes"),

    reloadTokenBtn: document.getElementById("reload-token-btn"),
};

/**
 * Simple async delay utility.
 */
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Return the panel-grid rectangle inside the rendered image.
 *
 * The browser gives us the displayed image size with getBoundingClientRect().
 * We then remove proportional margins used by axis labels/ticks.
 */
function getGridRect() {
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
 * Match the wrapper aspect ratio to the loaded image.
 *
 * This ensures:
 * - the wrapper dimensions match the real image dimensions
 * - hover overlays stay aligned
 * - different image sizes/aspect ratios work automatically
 */
function updateSpectrogramAspectRatio() {
    const image = elements.spectrogramImage;

    if (!image.naturalWidth || !image.naturalHeight) {
        return;
    }

    elements.spectrogramWrapper.style.aspectRatio =
        `${image.naturalWidth} / ${image.naturalHeight}`;
}

/**
 * Clamps value between min and max.
 * Used by resize handle.
 */
function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

/**
 * Sets the width of the right panel, saving the size to local storage.
 */
function setRightPanelWidth(width) {
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
function restoreRightPanelWidth() {
    const savedWidth = Number.parseInt(
        localStorage.getItem("rightPanelWidth"),
        10
    );

    if (Number.isInteger(savedWidth)) {
        setRightPanelWidth(savedWidth);
    }
}

/**
 * Show toast message. Toast is only shown when app encounters an error.
 */
function showToast(message, type = "danger") {
    const toastElement = document.createElement("div");
    toastElement.className = `toast align-items-center text-bg-${type} border-0`;
    toastElement.setAttribute("role", "alert");
    toastElement.setAttribute("aria-live", "assertive");
    toastElement.setAttribute("aria-atomic", "true");

    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body"></div>
            <button
                type="button"
                class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast"
                aria-label="Close"
            ></button>
        </div>
    `;

    toastElement.querySelector(".toast-body").textContent = message;
    elements.toastContainer.appendChild(toastElement);

    const toast = new bootstrap.Toast(toastElement, {
        autohide: type !== "danger",
        delay: 2500,
    });

    toastElement.addEventListener("hidden.bs.toast", () => {
        toastElement.remove();
    });

    toast.show();
}

/**
 * Called when spectrogram is fading out.
 */
async function fadeOutSpectrogram() {
    if (elements.spectrogramWrapper.classList.contains("d-none")) {
        return;
    }
    elements.spectrogramWrapper.classList.add("is-transitioning");
    await sleep(140);
}

/**
 * Called when spectrogram is fading in.
 */
function fadeInSpectrogram() {
    elements.spectrogramWrapper.classList.remove("is-transitioning");
}

/**
 * Border flash confirmation after submitting an annotation.
 */
function flashSaveConfirmation() {
    elements.spectrogramWrapper.classList.remove("save-confirmed");
    void elements.spectrogramWrapper.offsetWidth;
    elements.spectrogramWrapper.classList.add("save-confirmed");

    window.setTimeout(() => {
        elements.spectrogramWrapper.classList.remove("save-confirmed");
    }, 260);
}

/**
 * Convert null, undefined, or empty values into a display fallback.
 */
function displayValue(value, fallback = "—") {
    if (value === null || value === undefined || value === "") {
        return fallback;
    }

    return value;
}

/**
 * Read a panel input as an integer or null.
 */
function readPanelInput(inputElement) {
    const value = inputElement.value.trim();

    if (value === "") {
        return null;
    }

    return Number.parseInt(value, 10);
}

/**
 * Read all panel inputs as a list of integer or null.
 */
function readAllPanelInputs() {
    return [
        readPanelInput(elements.panelF1),
        readPanelInput(elements.panelF2),
        readPanelInput(elements.panelF3),
        readPanelInput(elements.panelF4),
    ];
}

/**
 * Returns whether all panels are valid.
 */
function panelsAreValid(panels) {
    return panels.every(
        (panel) =>
            Number.isInteger(panel) &&
            panel >= MIN_PANEL &&
            panel <= MAX_PANEL
    );
}

/**
 * Sets all panels given a panel number.
 */
function setAllPanelInputs(panelNumber) {
    elements.panelF1.value = panelNumber;
    elements.panelF2.value = panelNumber;
    elements.panelF3.value = panelNumber;
    elements.panelF4.value = panelNumber;
}

/**
 * Enable or disable annotation controls.
 */
function setControlsEnabled(enabled) {
    const controls = [
        elements.panelF1,
        elements.panelF2,
        elements.panelF3,
        elements.panelF4,
        elements.notes,
        elements.reloadTokenBtn,
    ];

    for (const control of controls) {
        control.disabled = !enabled;
    }
}

/**
 * Load and display annotation progress.
 */
async function loadProgress() {
    const response = await fetch(`/api/progress?annotator_id=${encodeURIComponent(annotatorId)}`);

    if (!response.ok) {
        throw new Error("Failed to load progress.");
    }

    const progress = await response.json();

    elements.progressLabel.textContent =
        `${progress.annotated_total} / ${progress.assigned_total} annotated ` +
        `(${progress.remaining_total} remaining)`;
}

/**
 * Load the next available token for this annotator.
 */
async function loadNextToken() {
    setControlsEnabled(false);
    hidePanelHoverOverlay();

    elements.emptyState.classList.remove("d-none");
    elements.emptyState.textContent = "Loading next token...";
    elements.spectrogramWrapper.classList.add("d-none");

    const response = await fetch(`/api/tokens/next?annotator_id=${encodeURIComponent(annotatorId)}`);

    if (!response.ok) {
        throw new Error("Failed to load next token.");
    }

    const token = await response.json();

    if (token === null) {
        currentToken = null;
        renderNoTokensRemaining();
        await loadProgress();
        return;
    }

    currentToken = token;
    renderToken(token);
    setControlsEnabled(true);
    await loadProgress();
}

/**
 * Display the no-tokens-left state.
 */
function renderNoTokensRemaining() {
    elements.tokenIdLabel.textContent = "Complete";
    elements.emptyState.classList.remove("d-none");
    elements.emptyState.textContent = "No remaining assigned tokens.";
    elements.spectrogramImage.classList.add("d-none");

    elements.metaWord.textContent = "—";
    elements.metaVowel.textContent = "—";
    elements.metaCorpus.textContent = "—";
    elements.metaSpeaker.textContent = "—";
    elements.metaContext.textContent = "—";
    elements.metaDuration.textContent = "—";
    elements.metaAutoWinner.textContent = "—";

    elements.audioPlayer.classList.add("d-none");
    elements.audioPlayer.removeAttribute("src");

    setAllPanelInputs("");
    elements.notes.value = "";

    setControlsEnabled(false);
    showToast("All assigned tokens have been annotated.", "success");
}

/**
 * Render one token in the UI.
 */
function renderToken(token) {
    const autoWinner = token.auto_winner_panel;

    elements.tokenIdLabel.textContent = token.id;

    elements.metaWord.textContent = displayValue(token.word);
    elements.metaVowel.textContent = displayValue(token.vowel_label);
    elements.metaCorpus.textContent = displayValue(token.corpus);
    elements.metaSpeaker.textContent = displayValue(token.speaker_id);

    elements.metaContext.textContent =
        `${displayValue(token.preceding_phone)} _ ${displayValue(token.following_phone)}`;

    elements.metaDuration.textContent =
        token.duration_ms === null || token.duration_ms === undefined
        ? "—"
        : `${token.duration_ms} ms`;

    elements.metaAutoWinner.textContent = autoWinner;

    setAllPanelInputs(autoWinner);
    elements.notes.value = "";

    elements.spectrogramImage.onload = () => {
        updateSpectrogramAspectRatio();
        fadeInSpectrogram();
    };

    elements.spectrogramWrapper.classList.add("is-transitioning");
    elements.spectrogramImage.src = token.image_url;
    elements.spectrogramWrapper.classList.remove("d-none");
    elements.emptyState.classList.add("d-none");

    if (token.audio_url) {
        elements.audioPlayer.src = token.audio_url;
        elements.audioPlayer.classList.remove("d-none");
    } else {
        elements.audioPlayer.classList.add("d-none");
        elements.audioPlayer.removeAttribute("src");
    }
}

/**
 * Hides panel hover overlay.
 */
function hidePanelHoverOverlay() {
    hoveredPanel = null;
    elements.panelHoverOverlay.classList.add("d-none");
}

/**
 * Converts mouse position to panel index assuming indices go
 * left-to-right then top-to-bottom.
 */
function getPanelFromMouseEvent(event) {
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
function updatePanelHoverOverlay(panelNumber) {
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
 * Handles mouse movement on the spectrogram image.
 */

function handleSpectrogramMouseMove(event) {
    if (!currentToken || isSaving) {
        hidePanelHoverOverlay();
        return;
    }

    const panelNumber = getPanelFromMouseEvent(event);

    if (panelNumber === null) {
        hidePanelHoverOverlay();
        return;
    }

    hoveredPanel = panelNumber;
    updatePanelHoverOverlay(panelNumber);
}

/**
 * Handles spectrogram click by setting all panels.
 * If shift-click, saves and then immedately submits annotation.
 */
async function handleSpectrogramClick(event) {
    if (!currentToken || hoveredPanel === null || isSaving) {
        return;
    }

    setAllPanelInputs(hoveredPanel);

    if (event.shiftKey) {
        await saveCurrentPanelFields();
    }
}

/**
 * Builds the base JSON payload
 */
function buildBasePayload(decision) {
    if (!currentToken) {
        throw new Error("No token is currently loaded.");
    }

    return {
        token_id: currentToken.id,
        annotator_id: annotatorId,
        decision: decision,
        notes: elements.notes.value.trim() || null,
    };
}

function buildAcceptAutoPayload() {
    return buildBasePayload("accept_auto");
}


function buildBadTokenPayload() {
    return buildBasePayload("bad_token");
}


function buildNeedsCorrectionPayload() {
    return buildBasePayload("needs_correction");
}

/**
 * Builds the JSON payload based on panel inputs.
 */
function buildPanelFieldPayload() {
    const panels = readAllPanelInputs();
    
    if (!panelsAreValid(panels)) {
        throw new Error(`F1-F4 panel values must be integers from ${MIN_PANEL} to ${MAX_PANEL}.`);
    }

    const [panelF1, panelF2, panelF3, panelF4] = panels;
    const uniquePanels = new Set(panels);
    const autoWinner = currentToken.auto_winner_panel;

    if (panels.every((panel) => panel === autoWinner)) {
        return {
            ...buildBasePayload("accept_auto"),
        };
    }

    if (uniquePanels.size === 1) {
        const selectedPanel = panelF1;

        return {
            ...buildBasePayload("select_panel"),
            selected_panel: selectedPanel,
            panel_f1: selectedPanel,
            panel_f2: selectedPanel,
            panel_f3: selectedPanel,
            panel_f4: selectedPanel,
        };
    }

    return {
        ...buildBasePayload("complex"),
        panel_f1: panelF1,
        panel_f2: panelF2,
        panel_f3: panelF3,
        panel_f4: panelF4,
    }
}

async function savePayload(payload) {
    if (!currentToken || isSaving) {
        return;
    }

    isSaving = true;
    setControlsEnabled(false);

    try {
        const response = await fetch("/api/annotations", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            const message = errorData?.detail || "Failed to save annotation.";
            throw new Error(message);
        }

        flashSaveConfirmation();
        await fadeOutSpectrogram();
        await loadNextToken();

    } catch (error) {
        showToast(error.message, "danger");
        setControlsEnabled(true);

    } finally {
        isSaving = false;
    }
}

async function saveAcceptAuto() {
    await savePayload(buildAcceptAutoPayload());
}

async function saveBadToken() {
    await savePayload(buildBadTokenPayload());
}

async function saveNeedsCorrection() {
    await savePayload(buildNeedsCorrectionPayload());
}

async function saveCurrentPanelFields() {
    await savePayload(buildPanelFieldPayload());
}

/**
 * Ignore hotkeys while the user is typing into form fields.
 */
function isTypingInInput(event) {
    const tagName = event.target.tagName.toLowerCase();

    return tagName === "input" || tagName === "textarea" || tagName === "select";
}

/**
 * Register button clicks and keyboard shortcuts
 */
function registerEventListeners() {
    elements.reloadTokenBtn.addEventListener("click", async () => {
        try {
            await loadNextToken();
        } catch (error) {
            showToast(error.message, "danger");
        }
    });

    elements.spectrogramWrapper.addEventListener("mousemove", handleSpectrogramMouseMove);
    elements.spectrogramWrapper.addEventListener("mouseleave", hidePanelHoverOverlay);
    elements.spectrogramWrapper.addEventListener("click", handleSpectrogramClick);

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

function registerResizeHandle() {
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

/**
 * Initialize the page.
 */
async function main() {
    registerEventListeners();
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