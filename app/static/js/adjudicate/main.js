/**
 * Read-only conflict-browser controller.
 *
 * The DOM is built with textContent rather than HTML interpolation so token
 * metadata and annotator notes are always rendered as text.
 */

const state = {
    batches: [],
    conflicts: [],
    selectedIndex: -1,
};

const elements = {
    batchSelect: document.querySelector("#batch-select"),
    statusAlert: document.querySelector("#status-alert"),
    conflictCount: document.querySelector("#conflict-count"),
    conflictList: document.querySelector("#conflict-list"),
    previousButton: document.querySelector("#previous-btn"),
    nextButton: document.querySelector("#next-btn"),
    tokenTitle: document.querySelector("#token-title"),
    tokenSubtitle: document.querySelector("#token-subtitle"),
    image: document.querySelector("#candidate-image"),
    imagePlaceholder: document.querySelector("#image-placeholder"),
    audioContainer: document.querySelector("#audio-container"),
    audio: document.querySelector("#token-audio"),
    metadataGrid: document.querySelector("#metadata-grid"),
    annotationRows: document.querySelector("#annotation-rows"),
};

async function apiGet(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
    });

    const response = await fetch(url);
    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const body = await response.json();
            detail = body.detail || detail;
        } catch {
            // Keep the status-based message if the response is not JSON.
        }
        throw new Error(detail);
    }
    return response.json();
}

function showStatus(message, kind = "info") {
    elements.statusAlert.textContent = message;
    elements.statusAlert.className = `alert alert-${kind} py-2`;
    elements.statusAlert.classList.remove("d-none");
}

function hideStatus() {
    elements.statusAlert.classList.add("d-none");
}

function clearElement(element) {
    while (element.firstChild) {
        element.firstChild.remove();
    }
}

function displayValue(value) {
    return value === null || value === undefined || value === "" ? "—" : String(value);
}

function renderBatchOptions() {
    clearElement(elements.batchSelect);

    state.batches.forEach((item, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = `${item.corpus} / ${item.batch} (${item.conflict_count})`;
        elements.batchSelect.append(option);
    });
    elements.batchSelect.disabled = state.batches.length === 0;
}

function renderConflictList() {
    clearElement(elements.conflictList);
    elements.conflictCount.textContent = String(state.conflicts.length);

    state.conflicts.forEach((conflict, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "list-group-item list-group-item-action conflict-list-item";
        if (index === state.selectedIndex) {
            button.classList.add("active");
        }

        const label = document.createElement("div");
        label.className = "token-label";
        label.textContent = `${conflict.batch_index + 1}. ${displayValue(conflict.phone)} ${displayValue(conflict.word)}`;

        const detail = document.createElement("div");
        detail.className = "small opacity-75";
        detail.textContent = `${displayValue(conflict.ipa)} · ${conflict.annotator_count} annotators`;

        button.append(label, detail);
        button.addEventListener("click", () => selectConflict(index));
        elements.conflictList.append(button);
    });
}

function renderMetadata(conflict) {
    const fields = [
        ["Token ID", conflict.token_id],
        ["File", conflict.file_stem],
        ["Speaker", conflict.speaker],
        ["Gender", conflict.gender],
        ["Discourse", conflict.discourse],
        ["Phone", conflict.phone],
        ["IPA", conflict.ipa],
        ["Word", conflict.word],
        ["Previous phone", conflict.previous_phone],
        ["Following phone", conflict.following_phone],
        ["Phone begin", conflict.phone_begin],
        ["Phone end", conflict.phone_end],
        ["Auto winner", conflict.auto_winner_panel],
        ["Candidates", conflict.n_candidates],
        ["Plot ceiling (Hz)", conflict.max_plotting_frequency],
    ];

    clearElement(elements.metadataGrid);
    for (const [label, value] of fields) {
        const item = document.createElement("dl");
        item.className = "metadata-item mb-0";
        const term = document.createElement("dt");
        term.textContent = label;
        const description = document.createElement("dd");
        description.textContent = displayValue(value);
        item.append(term, description);
        elements.metadataGrid.append(item);
    }
}

function panelCell(annotation, index) {
    const cell = document.createElement("td");
    cell.className = "panel-cell";
    cell.append(document.createTextNode(displayValue(annotation[`panel_f${index}`])));

    if (annotation[`needs_correction_f${index}`]) {
        const flag = document.createElement("span");
        flag.className = "correction-flag";
        flag.textContent = "needs correction";
        cell.append(flag);
    }
    return cell;
}

function renderAnnotations(annotations) {
    clearElement(elements.annotationRows);

    annotations.forEach((annotation) => {
        const row = document.createElement("tr");

        const annotator = document.createElement("th");
        annotator.scope = "row";
        annotator.textContent = annotation.annotator_id;

        const decision = document.createElement("td");
        decision.textContent = annotation.decision;

        const note = document.createElement("td");
        note.textContent = displayValue(annotation.note);

        row.append(
            annotator,
            decision,
            panelCell(annotation, 1),
            panelCell(annotation, 2),
            panelCell(annotation, 3),
            panelCell(annotation, 4),
            note,
        );
        elements.annotationRows.append(row);
    });
}

function renderMedia(conflict) {
    if (conflict.image_url) {
        elements.image.src = conflict.image_url;
        elements.image.classList.remove("d-none");
        elements.imagePlaceholder.classList.add("d-none");
    } else {
        elements.image.removeAttribute("src");
        elements.image.classList.add("d-none");
        elements.imagePlaceholder.textContent = "Candidate image is not available.";
        elements.imagePlaceholder.classList.remove("d-none");
    }

    if (conflict.audio_url) {
        elements.audio.src = conflict.audio_url;
        elements.audioContainer.classList.remove("d-none");
    } else {
        elements.audio.removeAttribute("src");
        elements.audioContainer.classList.add("d-none");
    }
}

function updateNavigation() {
    elements.previousButton.disabled = state.selectedIndex <= 0;
    elements.nextButton.disabled =
        state.selectedIndex < 0 || state.selectedIndex >= state.conflicts.length - 1;
}

async function selectConflict(index) {
    const summary = state.conflicts[index];
    if (!summary) {
        return;
    }

    state.selectedIndex = index;
    renderConflictList();
    updateNavigation();
    showStatus(`Loading token ${summary.batch_index + 1}…`);

    try {
        const conflict = await apiGet("/api/adjudication/conflict", {
            token_id: summary.token_id,
        });
        elements.tokenTitle.textContent =
            `${displayValue(conflict.phone)} ${displayValue(conflict.ipa)} — ${displayValue(conflict.word)}`;
        elements.tokenSubtitle.textContent =
            `${conflict.corpus} / ${conflict.batch} / index ${conflict.batch_index + 1}`;
        renderMetadata(conflict);
        renderAnnotations(conflict.annotations);
        renderMedia(conflict);
        hideStatus();
    } catch (error) {
        showStatus(error.message, "danger");
    }
}

async function loadSelectedBatch() {
    const selected = state.batches[Number(elements.batchSelect.value)];
    if (!selected) {
        return;
    }

    showStatus(`Loading conflicts for ${selected.corpus} / ${selected.batch}…`);
    try {
        state.conflicts = await apiGet("/api/adjudication/conflicts", {
            corpus: selected.corpus,
            batch: selected.batch,
        });
        state.selectedIndex = -1;
        renderConflictList();
        updateNavigation();

        if (state.conflicts.length > 0) {
            await selectConflict(0);
        } else {
            showStatus("This batch has no current conflicts.", "success");
        }
    } catch (error) {
        showStatus(error.message, "danger");
    }
}

async function initialize() {
    try {
        state.batches = await apiGet("/api/adjudication/batches");
        renderBatchOptions();
        if (state.batches.length === 0) {
            showStatus("No current conflicts were found.", "success");
            return;
        }
        await loadSelectedBatch();
    } catch (error) {
        showStatus(error.message, "danger");
    }
}

elements.batchSelect.addEventListener("change", loadSelectedBatch);
elements.previousButton.addEventListener("click", () => {
    selectConflict(state.selectedIndex - 1);
});
elements.nextButton.addEventListener("click", () => {
    selectConflict(state.selectedIndex + 1);
});
elements.image.addEventListener("error", () => {
    elements.image.classList.add("d-none");
    elements.imagePlaceholder.textContent = "Candidate image could not be loaded.";
    elements.imagePlaceholder.classList.remove("d-none");
});

initialize();
