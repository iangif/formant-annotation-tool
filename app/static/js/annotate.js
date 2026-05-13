/*

    Frontend logic.

    Responsibilities:
    1. load the next token from the backend
    2. display its spectrogram image and metadata
    3. keep F1-F4 panel fields initialized to the auto winner
    4. save annotation decisions through the API
    5. load the next token after each save

    Current hotkeys:
    - Enter: accept automatic winner
    - B: mark bad token
    - X: mark needs correction
*/

let currentToken = null;
let isSaving = false;

const annotatorId = document.getElementById("annotator-id").textContent.trim();

const elements = {
    progressLabel: document.getElementById("progress-label"),
    statusAlert: document.getElementById("status-alert"),

    emptyState: document.getElementById("empty-state"),
    spectrogramImage: document.getElementById("spectrogram-image"),

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
    acceptAutoBtn: document.getElementById("accept-auto-btn"),
    badTokenBtn: document.getElementById("bad-token-btn"),
    needsCorrectionBtn: document.getElementById("needs-correction-btn"),
}

/**
 * Show a Bootstrap-style status message.
 */
function showStatus(message, type = "info") {
    elements.statusAlert.textContent = message;
    elements.statusAlert.className = `alert alert-${type}`;
}

/**
 * Hide the status message.
 */
function clearStatus() {
    elements.statusAlert.textContent = "";
    elements.statusAlert.className = "alert d-none";
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
 * Enable or disable annotation controls.
 */
function setControlsEnabled(enabled) {
    const controls = [
        elements.panelF1,
        elements.panelF2,
        elements.panelF3,
        elements.panelF4,
        elements.notes,
        elements.acceptAutoBtn,
        elements.badTokenBtn,
        elements.needsCorrectionBtn,
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
    clearStatus();
    setControlsEnabled(false);

    elements.emptyState.classList.remove("d-none");
    elements.emptyState.textContent = "Loading next token...";
    elements.spectrogramImage.classList.add("d-none");

    const response = await fetch(`/api/tokens/next?annotator_id=${encodeURIComponent(annotatorId)}`);

    if (!response.ok) {
        throw new Error("Failed to load next token.");
    }

    const token = await response.json();

    if (token == null) {
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

    elements.panelF1.value = "";
    elements.panelF2.value = "";
    elements.panelF3.value = "";
    elements.panelF4.value = "";
    elements.notes.value = "";

    setControlsEnabled(false);
    showStatus("All assigned tokens have been annotated.", "success");
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

    elements.panelF1.value = autoWinner;
    elements.panelF2.value = autoWinner;
    elements.panelF3.value = autoWinner;
    elements.panelF4.value = autoWinner;

    elements.notes.value = "";

    elements.spectrogramImage.src = token.image_url;
    elements.spectrogramImage.classList.remove("d-none");
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
 * Build the JSON payload sent to POST /api/annotations
 */
function buildAnnotationPayload(decision) {
    if (!currentToken) {
        throw new Error("No token is currently loaded.");
    }

    return {
        token_id: currentToken.id,
        annotator_id: annotatorId,
        decision: decision,

        panel_f1: readPanelInput(elements.panelF1),
        panel_f2: readPanelInput(elements.panelF2),
        panel_f3: readPanelInput(elements.panelF3),
        panel_f4: readPanelInput(elements.panelF4),

        notes: elements.notes.value.trim() || null,
    };
}

/**
 * Save one annotation and then load the next token.
 */
async function saveAnnotation(decision) {
    if (!currentToken || isSaving) {
        return;
    }

    isSaving = true;
    setControlsEnabled(false);
    showStatus("Saving annotation...", "info");

    try {
        const payload = buildAnnotationPayload(decision);

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

        showStatus("Annotation saved.", "success");
        await loadNextToken();

    } catch (error) {
        showStatus(error.message, "danger");
        setControlsEnabled(true);

    } finally {
        isSaving = false;
    }
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
            showStatus(error.message, "danger");
        }
    });

    elements.acceptAutoBtn.addEventListener("click", () => {
        saveAnnotation("accept_auto");
    });

    elements.badTokenBtn.addEventListener("click", () => {
        saveAnnotation("needs_correction");
    });

    elements.needsCorrectionBtn.addEventListener("click", () => {
        saveAnnotation("needs_correction");
    });

    document.addEventListener("keydown", (event) => {
        if (isTypingInInput(event)) {
            return;
        }

        if (event.key === "Enter") {
            event.preventDefault();
            saveAnnotation("accept_auto");
        }

        if (event.key.toLowerCase() === "b") {
            event.preventDefault();
            saveAnnotation("bad_token");
        }

        if (event.key.toLowerCase() === "x") {
            event.preventDefault();
            saveAnnotation("needs_correction");
        }
    });
}

/**
 * Initialize the page.
 */
async function main() {
    registerEventListeners();

    try {
        await loadNextToken();
    } catch (error) {
        showStatus(error.message, "danger");
        setControlsEnabled(false);
    }
}

main();