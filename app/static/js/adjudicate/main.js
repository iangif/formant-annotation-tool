/**
 * Interactive adjudication comparison workspace.
 *
 * Draft decisions live only in this page's JavaScript memory. The preview POST
 * endpoint renders a supplied draft but never stores it.
 */

const PANEL_COLUMNS = 5;
const DEFAULT_PANEL_ROWS = 4;
const GRID_OFFSET = {
    left: 0.05,
    right: 0.01,
    top: 0,
    bottom: 0.05,
};
const ANNOTATOR_COLORS = [
    "#0072b2",
    "#d55e00",
    "#009e73",
    "#cc79a7",
    "#e69f00",
    "#56b4e9",
    "#6f42c1",
    "#795548",
];
const DRAFT_COLOR = "#d39e00";
const PREVIEW_DEBOUNCE_MS = 300;

const state = {
    batches: [],
    conflicts: [],
    selectedIndex: -1,
    currentConflict: null,
    activeView: "candidate",
    focusedFormant: 1,
    drafts: new Map(),
    automaticProposals: new Map(),
    detailRequestVersion: 0,
    previewRequestVersion: 0,
    proposalRequestVersion: 0,
    previewTimer: null,
    draftPreviewUrl: null,
};

const elements = {
    batchSelect: document.querySelector("#batch-select"),
    statusAlert: document.querySelector("#status-alert"),
    conflictCount: document.querySelector("#conflict-count"),
    conflictList: document.querySelector("#conflict-list"),
    previousButton: document.querySelector("#previous-btn"),
    nextButton: document.querySelector("#next-btn"),
    candidateViewButton: document.querySelector("#candidate-view-btn"),
    tracksViewButton: document.querySelector("#tracks-view-btn"),
    candidateView: document.querySelector("#candidate-view"),
    tracksView: document.querySelector("#tracks-view"),
    tokenTitle: document.querySelector("#token-title"),
    tokenSubtitle: document.querySelector("#token-subtitle"),
    image: document.querySelector("#candidate-image"),
    imageWrapper: document.querySelector("#candidate-grid-wrapper"),
    imagePlaceholder: document.querySelector("#image-placeholder"),
    overlayLayer: document.querySelector("#candidate-overlay-layer"),
    annotatorLegend: document.querySelector("#annotator-legend"),
    unplacedCorrectionAlert: document.querySelector("#unplaced-correction-alert"),
    trackComparisonGrid: document.querySelector("#track-comparison-grid"),
    audioContainer: document.querySelector("#audio-container"),
    audio: document.querySelector("#token-audio"),
    metadataGrid: document.querySelector("#metadata-grid"),
    annotationRows: document.querySelector("#annotation-rows"),
    draftFormants: document.querySelector("#draft-formants"),
    draftPanelInputs: [...document.querySelectorAll(".draft-panel-input")],
    draftCorrectionInputs: [...document.querySelectorAll(".draft-correction-input")],
    draftNote: document.querySelector("#draft-note"),
    draftStatus: document.querySelector("#draft-status"),
    draftResolutionType: document.querySelector("#draft-resolution-type"),
    resetDraftButton: document.querySelector("#reset-draft-btn"),
    averageTracksButton: document.querySelector("#average-tracks-btn"),
    randomTrackButton: document.querySelector("#random-track-btn"),
    randomSeedInput: document.querySelector("#automatic-random-seed"),
    includeNeedsCorrectionInput: document.querySelector(
        "#automatic-include-needs-correction",
    ),
    automaticProposalStatus: document.querySelector("#automatic-proposal-status"),
    useAutomaticProposalButton: document.querySelector(
        "#use-automatic-proposal-btn",
    ),
};


// ---------------------------------------------------------------------------
// API and general DOM helpers
// ---------------------------------------------------------------------------

async function responseError(response) {
    let detail = `Request failed (${response.status})`;
    try {
        const body = await response.json();
        detail = body.detail || detail;
    } catch {
        // Keep the status-based message when the response is not JSON.
    }
    return new Error(detail);
}

async function apiGet(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
    });

    const response = await fetch(url);
    if (!response.ok) {
        throw await responseError(response);
    }
    return response.json();
}

async function apiPostImage(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        throw await responseError(response);
    }
    return response.blob();
}

async function apiPostJson(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        throw await responseError(response);
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
    element.replaceChildren();
}

function displayValue(value) {
    return value === null || value === undefined || value === "" ? "—" : String(value);
}

function hasSelectedPanel(annotation) {
    return [1, 2, 3, 4].some(
        (number) => annotation[`panel_f${number}`] !== null
            && annotation[`panel_f${number}`] !== undefined,
    );
}

function annotatorColor(index) {
    return ANNOTATOR_COLORS[index % ANNOTATOR_COLORS.length];
}

function setColorVariable(element, color) {
    element.style.setProperty("--annotator-color", color);
}


// ---------------------------------------------------------------------------
// Corpus/batch and conflict navigation
// ---------------------------------------------------------------------------

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
        label.textContent =
            `${conflict.batch_index + 1}. ${displayValue(conflict.phone)} ${displayValue(conflict.word)}`;

        const detail = document.createElement("div");
        detail.className = "small opacity-75";
        detail.textContent =
            `${displayValue(conflict.ipa)} · ${conflict.annotator_count} annotators`;

        button.append(label, detail);
        button.addEventListener("click", () => selectConflict(index));
        elements.conflictList.append(button);
    });
}

function updateNavigation() {
    elements.previousButton.disabled = state.selectedIndex <= 0;
    elements.nextButton.disabled =
        state.selectedIndex < 0 || state.selectedIndex >= state.conflicts.length - 1;
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


// ---------------------------------------------------------------------------
// Annotation table
// ---------------------------------------------------------------------------

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

function renderAnnotations(conflict) {
    clearElement(elements.annotationRows);

    conflict.annotations.forEach((annotation, annotatorIndex) => {
        const row = document.createElement("tr");

        const annotator = document.createElement("th");
        annotator.scope = "row";
        const annotatorKey = document.createElement("span");
        annotatorKey.className = "annotator-key";
        setColorVariable(annotatorKey, annotatorColor(annotatorIndex));
        annotatorKey.textContent = annotation.annotator_id;
        annotator.append(annotatorKey);

        const decision = document.createElement("td");
        decision.textContent = annotation.decision;

        const note = document.createElement("td");
        note.textContent = displayValue(annotation.note);

        const action = document.createElement("td");
        const useButton = document.createElement("button");
        useButton.type = "button";
        useButton.className = "btn btn-outline-primary btn-sm text-nowrap";
        useButton.textContent = "Use annotation";
        useButton.addEventListener("click", () => useAnnotation(annotation));
        action.append(useButton);

        row.append(
            annotator,
            decision,
            panelCell(annotation, 1),
            panelCell(annotation, 2),
            panelCell(annotation, 3),
            panelCell(annotation, 4),
            note,
            action,
        );
        elements.annotationRows.append(row);
    });
}


// ---------------------------------------------------------------------------
// Browser-only draft
// ---------------------------------------------------------------------------

function blankDraft() {
    return {
        resolution_type: "manual_panels",
        resolution_recipe: null,
        source_fingerprint: null,
        automatic_summary: null,
        random_seed: null,
        include_needs_correction: false,
        automatic_preview_url: null,
        panel_f1: null,
        panel_f2: null,
        panel_f3: null,
        panel_f4: null,
        needs_correction_f1: false,
        needs_correction_f2: false,
        needs_correction_f3: false,
        needs_correction_f4: false,
        note: "",
    };
}

function currentDraft() {
    if (!state.currentConflict) {
        return null;
    }
    if (!state.drafts.has(state.currentConflict.token_id)) {
        state.drafts.set(state.currentConflict.token_id, blankDraft());
    }
    return state.drafts.get(state.currentConflict.token_id);
}

function readPanelInput(input) {
    const value = input.value.trim();
    if (value === "") {
        return null;
    }
    if (!/^\d+$/.test(value)) {
        return Number.NaN;
    }
    return Number.parseInt(value, 10);
}

function draftValidation(draft) {
    if (
        ["average_tracks", "random_track"].includes(draft.resolution_type)
        && draft.resolution_recipe
    ) {
        return {
            valid: true,
            errors: new Map(),
            message: `${draft.automatic_summary} Draft remains unsaved.`,
        };
    }

    const errors = new Map();
    const candidateCount = Number.isInteger(state.currentConflict?.n_candidates)
        ? state.currentConflict.n_candidates
        : PANEL_COLUMNS * DEFAULT_PANEL_ROWS;
    const maximumPanel = candidateCount - 1;

    for (let number = 1; number <= 4; number += 1) {
        const panel = draft[`panel_f${number}`];
        if (
            panel !== null
            && (!Number.isInteger(panel) || panel < 0 || panel > maximumPanel)
        ) {
            errors.set(
                number,
                `F${number} must be blank or an integer from 0 to ${maximumPanel}.`,
            );
        }
    }

    if (
        errors.size === 0
        && ![1, 2, 3, 4].some((number) => draft[`panel_f${number}`] !== null)
    ) {
        return {
            valid: false,
            errors,
            message: "Select at least one formant panel to preview the draft.",
        };
    }
    if (errors.size > 0) {
        return {
            valid: false,
            errors,
            message: [...errors.values()].join(" "),
        };
    }
    return {
        valid: true,
        errors,
        message: draft.resolution_type === "choose_annotation"
            ? "Selected annotation is valid and remains unsaved."
            : "Manual-panel draft is valid and remains unsaved.",
    };
}

function setDraftControlsEnabled(enabled) {
    [
        ...elements.draftPanelInputs,
        ...elements.draftCorrectionInputs,
        elements.draftNote,
    ].forEach((element) => {
        element.disabled = !enabled;
    });
    elements.resetDraftButton.disabled = !enabled;
    const previewsAvailable = enabled && Boolean(
        state.currentConflict?.track_preview_available,
    );
    elements.averageTracksButton.disabled = !previewsAvailable;
    elements.randomTrackButton.disabled = !previewsAvailable;
    elements.randomSeedInput.disabled = !previewsAvailable;
    elements.includeNeedsCorrectionInput.disabled = !previewsAvailable;
}

function displayResolutionType(resolutionType) {
    return {
        manual_panels: "manual panels",
        choose_annotation: "chosen annotation",
        average_tracks: "average tracks",
        random_track: "random track",
    }[resolutionType] || resolutionType;
}

function renderDraftResolutionType() {
    const draft = currentDraft();
    elements.draftResolutionType.textContent = displayResolutionType(
        draft?.resolution_type || "manual_panels",
    );
}

function writeDraftToControls() {
    const draft = currentDraft();
    if (!draft) {
        return;
    }
    for (const input of elements.draftPanelInputs) {
        const number = Number(input.dataset.formant);
        input.value = draft[`panel_f${number}`] ?? "";
    }
    for (const input of elements.draftCorrectionInputs) {
        const number = Number(input.dataset.formant);
        input.checked = Boolean(draft[`needs_correction_f${number}`]);
    }
    elements.draftNote.value = draft.note;
    renderDraftResolutionType();
    setFocusedFormant(state.focusedFormant);
}

function readControlsIntoDraft() {
    const draft = currentDraft();
    if (!draft) {
        return;
    }
    for (const input of elements.draftPanelInputs) {
        const number = Number(input.dataset.formant);
        draft[`panel_f${number}`] = readPanelInput(input);
    }
    for (const input of elements.draftCorrectionInputs) {
        const number = Number(input.dataset.formant);
        draft[`needs_correction_f${number}`] = input.checked;
    }
    draft.note = elements.draftNote.value;
}

function setFocusedFormant(number) {
    state.focusedFormant = number;
    for (const container of elements.draftFormants.querySelectorAll(".draft-formant")) {
        container.classList.toggle(
            "is-focused",
            Number(container.dataset.formant) === number,
        );
    }
}

function updateDraftValidation() {
    const draft = currentDraft();
    if (!draft) {
        return {valid: false, errors: new Map(), message: ""};
    }
    const validation = draftValidation(draft);

    for (const container of elements.draftFormants.querySelectorAll(".draft-formant")) {
        container.classList.toggle(
            "is-invalid",
            validation.errors.has(Number(container.dataset.formant)),
        );
    }
    elements.draftStatus.textContent = validation.message;
    elements.draftStatus.className = validation.valid
        ? "small text-success mt-3"
        : "small text-muted mt-3";
    return validation;
}

function useAnnotation(annotation) {
    const draft = currentDraft();
    if (!draft) {
        return;
    }
    releaseDraftAutomaticPreview(draft);
    for (let number = 1; number <= 4; number += 1) {
        draft[`panel_f${number}`] = annotation[`panel_f${number}`];
        draft[`needs_correction_f${number}`] = Boolean(
            annotation[`needs_correction_f${number}`],
        );
    }
    draft.resolution_type = "choose_annotation";
    draft.resolution_recipe = {
        type: "selected_annotation",
        method: "choose_annotation",
        source_annotation_ids: [annotation.central_annotation_id],
        selected_annotation_id: annotation.central_annotation_id,
    };
    draft.source_fingerprint = null;
    draft.automatic_summary = null;
    draft.random_seed = null;
    draft.include_needs_correction = false;
    writeDraftToControls();
    draftChanged();
}

function resetDraft() {
    if (!state.currentConflict) {
        return;
    }
    releaseDraftAutomaticPreview(currentDraft());
    state.drafts.set(state.currentConflict.token_id, blankDraft());
    writeDraftToControls();
    draftChanged();
}

function draftChanged() {
    renderDraftResolutionType();
    renderCandidateOverlays();
    renderUnplacedCorrectionWarning();
    const validation = updateDraftValidation();
    scheduleDraftPreview(validation);
}

function changeDraftToManualPanels() {
    const draft = currentDraft();
    if (!draft) {
        return;
    }
    releaseDraftAutomaticPreview(draft);
    draft.resolution_type = "manual_panels";
    draft.resolution_recipe = {
        type: "selected_panels",
        method: "manual_panels",
        source_annotation_ids: [],
    };
    draft.source_fingerprint = null;
    draft.automatic_summary = null;
    draft.random_seed = null;
    draft.include_needs_correction = false;
}


// ---------------------------------------------------------------------------
// Automatic random/average proposals
// ---------------------------------------------------------------------------

function currentAutomaticProposal() {
    if (!state.currentConflict) {
        return null;
    }
    return state.automaticProposals.get(state.currentConflict.token_id) || null;
}

function releaseAutomaticProposal(proposal) {
    if (proposal?.previewUrl) {
        URL.revokeObjectURL(proposal.previewUrl);
    }
}

function invalidateAutomaticProposals() {
    state.proposalRequestVersion += 1;
    state.automaticProposals.forEach(releaseAutomaticProposal);
    state.automaticProposals.clear();
    renderAutomaticProposalStatus();
    if (state.currentConflict) {
        renderTrackCards(state.currentConflict);
        setDraftControlsEnabled(true);
    }
}

function releaseDraftAutomaticPreview(draft) {
    if (draft?.automatic_preview_url) {
        URL.revokeObjectURL(draft.automatic_preview_url);
        draft.automatic_preview_url = null;
    }
}

function renderAutomaticProposalStatus() {
    const proposal = currentAutomaticProposal();
    if (!state.currentConflict) {
        elements.automaticProposalStatus.textContent =
            "Select a conflict to generate a proposal.";
        elements.useAutomaticProposalButton.classList.add("d-none");
        return;
    }
    if (!state.currentConflict.track_preview_available) {
        elements.automaticProposalStatus.textContent =
            "Automatic previews require the token pickle and plotting frequency.";
        elements.useAutomaticProposalButton.classList.add("d-none");
        return;
    }
    if (!proposal) {
        elements.automaticProposalStatus.textContent =
            "Choose a method to generate an unsaved proposal.";
        elements.useAutomaticProposalButton.classList.add("d-none");
        return;
    }

    const excluded = proposal.metadata.excluded_annotations;
    const exclusionText = excluded.length === 0
        ? "No displayed annotations were excluded."
        : `Excluded: ${excluded.map(
            (source) => `${source.annotator_id} (${source.reason})`,
        ).join("; ")}.`;
    const correctionPolicyText = proposal.metadata.include_needs_correction
        ? "Needs-correction flags were ignored for eligibility."
        : "Needs-correction annotations were excluded.";
    elements.automaticProposalStatus.textContent =
        `${proposal.metadata.summary} ${correctionPolicyText} ${exclusionText}`;
    elements.useAutomaticProposalButton.classList.remove("d-none");
}

function proposalRequestPayload(method) {
    const seed = Number.parseInt(elements.randomSeedInput.value, 10);
    return {
        token_id: state.currentConflict.token_id,
        method,
        random_seed: Number.isInteger(seed) ? seed : 0,
        include_needs_correction: elements.includeNeedsCorrectionInput.checked,
    };
}

async function generateAutomaticProposal(method) {
    if (!state.currentConflict?.track_preview_available) {
        renderAutomaticProposalStatus();
        return;
    }

    state.proposalRequestVersion += 1;
    const requestVersion = state.proposalRequestVersion;
    const tokenId = state.currentConflict.token_id;
    const payload = proposalRequestPayload(method);
    elements.averageTracksButton.disabled = true;
    elements.randomTrackButton.disabled = true;
    elements.randomSeedInput.disabled = true;
    elements.includeNeedsCorrectionInput.disabled = true;
    elements.automaticProposalStatus.textContent =
        `Building ${displayResolutionType(method)} proposal…`;
    elements.useAutomaticProposalButton.classList.add("d-none");

    try {
        const [metadata, previewBlob] = await Promise.all([
            apiPostJson("/api/adjudication/automatic-proposal", payload),
            apiPostImage("/api/adjudication/automatic-preview", payload),
        ]);
        if (
            requestVersion !== state.proposalRequestVersion
            || state.currentConflict?.token_id !== tokenId
        ) {
            return;
        }

        const previous = state.automaticProposals.get(tokenId);
        releaseAutomaticProposal(previous);
        state.automaticProposals.set(tokenId, {
            metadata,
            previewBlob,
            previewUrl: URL.createObjectURL(previewBlob),
        });
        renderAutomaticProposalStatus();
        renderTrackCards(state.currentConflict);
        setComparisonView("tracks");
    } catch (error) {
        if (requestVersion === state.proposalRequestVersion) {
            elements.automaticProposalStatus.textContent =
                `Automatic proposal error: ${error.message}`;
            elements.useAutomaticProposalButton.classList.add("d-none");
        }
    } finally {
        if (
            requestVersion === state.proposalRequestVersion
            && state.currentConflict?.token_id === tokenId
        ) {
            setDraftControlsEnabled(true);
        }
    }
}

function useAutomaticProposal() {
    const proposal = currentAutomaticProposal();
    const draft = currentDraft();
    if (!proposal || !draft) {
        return;
    }

    const metadata = proposal.metadata;
    releaseDraftAutomaticPreview(draft);
    draft.resolution_type = metadata.resolution_type;
    draft.resolution_recipe = metadata.recipe;
    draft.source_fingerprint = metadata.source_fingerprint;
    draft.automatic_summary = metadata.summary;
    draft.random_seed = metadata.random_seed;
    draft.include_needs_correction = Boolean(
        metadata.include_needs_correction,
    );
    draft.automatic_preview_url = URL.createObjectURL(proposal.previewBlob);

    const selectedId = metadata.recipe.selected_annotation_id;
    const selected = state.currentConflict.annotations.find(
        (annotation) => annotation.central_annotation_id === selectedId,
    );
    for (let number = 1; number <= 4; number += 1) {
        draft[`panel_f${number}`] = selected
            ? selected[`panel_f${number}`]
            : null;
        draft[`needs_correction_f${number}`] = selected
            ? Boolean(selected[`needs_correction_f${number}`])
            : false;
    }

    writeDraftToControls();
    draftChanged();
}


// ---------------------------------------------------------------------------
// Candidate-grid annotations and focused-formant clicking
// ---------------------------------------------------------------------------

function selectionsByPanel(conflict) {
    const selections = new Map();

    function add(panel, selection) {
        if (panel === null || panel === undefined) {
            return;
        }
        if (!selections.has(panel)) {
            selections.set(panel, []);
        }
        selections.get(panel).push(selection);
    }

    conflict.annotations.forEach((annotation, annotatorIndex) => {
        const groups = new Map();
        for (let number = 1; number <= 4; number += 1) {
            const panel = annotation[`panel_f${number}`];
            if (panel === null || panel === undefined) {
                continue;
            }
            if (!groups.has(panel)) {
                groups.set(panel, []);
            }
            const warning = annotation[`needs_correction_f${number}`] ? "⚠" : "";
            groups.get(panel).push(`F${number}${warning}`);
        }
        groups.forEach((formants, panel) => {
            add(panel, {
                label: `${annotation.annotator_id}: ${formants.join(" ")}`,
                color: annotatorColor(annotatorIndex),
                draft: false,
            });
        });
    });

    const draft = currentDraft();
    if (draft) {
        const groups = new Map();
        for (let number = 1; number <= 4; number += 1) {
            const panel = draft[`panel_f${number}`];
            if (!Number.isInteger(panel)) {
                continue;
            }
            if (!groups.has(panel)) {
                groups.set(panel, []);
            }
            const warning = draft[`needs_correction_f${number}`] ? "⚠" : "";
            groups.get(panel).push(`F${number}${warning}`);
        }
        groups.forEach((formants, panel) => {
            add(panel, {
                label: `Draft: ${formants.join(" ")}`,
                color: DRAFT_COLOR,
                draft: true,
            });
        });
    }
    return selections;
}

function selectPanelForFocusedFormant(panel) {
    const draft = currentDraft();
    if (!draft) {
        return;
    }
    changeDraftToManualPanels();
    const number = state.focusedFormant;
    draft[`panel_f${number}`] = panel;
    const input = elements.draftPanelInputs.find(
        (item) => Number(item.dataset.formant) === number,
    );
    input.value = String(panel);
    input.focus({preventScroll: true});
    draftChanged();
}

function renderCandidateOverlays() {
    clearElement(elements.overlayLayer);
    if (!state.currentConflict) {
        return;
    }

    const selections = selectionsByPanel(state.currentConflict);
    const candidateCount = Number.isInteger(state.currentConflict.n_candidates)
        ? state.currentConflict.n_candidates
        : PANEL_COLUMNS * DEFAULT_PANEL_ROWS;
    const rows = Math.max(1, Math.ceil(candidateCount / PANEL_COLUMNS));
    const gridWidth = 1 - GRID_OFFSET.left - GRID_OFFSET.right;
    const gridHeight = 1 - GRID_OFFSET.top - GRID_OFFSET.bottom;
    const panelWidth = gridWidth / PANEL_COLUMNS;
    const panelHeight = gridHeight / rows;

    for (let panel = 0; panel < candidateCount; panel += 1) {
        const column = panel % PANEL_COLUMNS;
        const row = Math.floor(panel / PANEL_COLUMNS);
        const target = document.createElement("button");
        target.type = "button";
        target.className = "candidate-panel-target";
        target.style.left = `${(GRID_OFFSET.left + column * panelWidth) * 100}%`;
        target.style.top = `${(GRID_OFFSET.top + row * panelHeight) * 100}%`;
        target.style.width = `${panelWidth * 100}%`;
        target.style.height = `${panelHeight * 100}%`;

        const panelSelections = selections.get(panel) || [];
        if (panelSelections.length > 0) {
            const badges = document.createElement("span");
            badges.className = "panel-badges";
            panelSelections.forEach((selection) => {
                const badge = document.createElement("span");
                badge.className = "panel-selection-badge";
                if (selection.draft) {
                    badge.classList.add("is-draft");
                    target.classList.add("has-draft-selection");
                }
                setColorVariable(badge, selection.color);
                badge.textContent = selection.label;
                badges.append(badge);
            });
            target.append(badges);
        }

        const selectionDescription = panelSelections.length > 0
            ? `; ${panelSelections.map((item) => item.label).join("; ")}`
            : "";
        target.setAttribute(
            "aria-label",
            `Panel ${panel}; set focused F${state.focusedFormant}${selectionDescription}`,
        );
        target.addEventListener("click", () => selectPanelForFocusedFormant(panel));
        elements.overlayLayer.append(target);
    }
}

function renderAnnotatorLegend(conflict) {
    clearElement(elements.annotatorLegend);
    conflict.annotations.forEach((annotation, index) => {
        const item = document.createElement("span");
        item.className = "legend-item";
        setColorVariable(item, annotatorColor(index));
        const swatch = document.createElement("span");
        swatch.className = "legend-swatch";
        const label = document.createElement("span");
        label.textContent = annotation.annotator_id;
        item.append(swatch, label);
        elements.annotatorLegend.append(item);
    });

    const draftItem = document.createElement("span");
    draftItem.className = "legend-item";
    setColorVariable(draftItem, DRAFT_COLOR);
    const draftSwatch = document.createElement("span");
    draftSwatch.className = "legend-swatch";
    const draftLabel = document.createElement("span");
    draftLabel.textContent = "Unsaved draft";
    draftItem.append(draftSwatch, draftLabel);
    elements.annotatorLegend.append(draftItem);
}

function renderUnplacedCorrectionWarning() {
    if (!state.currentConflict) {
        elements.unplacedCorrectionAlert.classList.add("d-none");
        return;
    }
    const unplaced = [];
    state.currentConflict.annotations.forEach((annotation) => {
        for (let number = 1; number <= 4; number += 1) {
            if (
                annotation[`needs_correction_f${number}`]
                && annotation[`panel_f${number}`] === null
            ) {
                unplaced.push(`${annotation.annotator_id}: F${number}`);
            }
        }
    });
    const draft = currentDraft();
    if (draft) {
        for (let number = 1; number <= 4; number += 1) {
            if (
                draft[`needs_correction_f${number}`]
                && draft[`panel_f${number}`] === null
            ) {
                unplaced.push(`Draft: F${number}`);
            }
        }
    }

    if (unplaced.length === 0) {
        elements.unplacedCorrectionAlert.classList.add("d-none");
        return;
    }
    elements.unplacedCorrectionAlert.textContent =
        `Correction flags without a panel: ${unplaced.join(", ")}. `
        + "These formants are intentionally absent from track previews.";
    elements.unplacedCorrectionAlert.classList.remove("d-none");
}


// ---------------------------------------------------------------------------
// Separate selected-track previews
// ---------------------------------------------------------------------------

function previewCard(title, color, action = null) {
    const card = document.createElement("article");
    card.className = "track-preview-card";
    const header = document.createElement("div");
    header.className = "track-preview-header";
    const label = document.createElement("span");
    label.className = "annotator-key";
    setColorVariable(label, color);
    label.textContent = title;
    header.append(label);
    if (action) {
        header.append(action);
    }
    const body = document.createElement("div");
    body.className = "track-preview-body";
    card.append(header, body);
    return {card, body};
}

function previewMessage(body, message) {
    clearElement(body);
    const placeholder = document.createElement("div");
    placeholder.className = "track-preview-message";
    placeholder.textContent = message;
    body.append(placeholder);
}

function previewImage(body, source, alt) {
    clearElement(body);
    const image = document.createElement("img");
    image.className = "track-preview-image";
    image.alt = alt;
    image.src = source;
    image.addEventListener("error", () => {
        previewMessage(body, "This selected track could not be rendered.");
    });
    body.append(image);
}

function renderTrackCards(conflict) {
    clearElement(elements.trackComparisonGrid);

    conflict.annotations.forEach((annotation, index) => {
        const useButton = document.createElement("button");
        useButton.type = "button";
        useButton.className = "btn btn-outline-primary btn-sm";
        useButton.textContent = "Use";
        useButton.addEventListener("click", () => useAnnotation(annotation));

        const {card, body} = previewCard(
            annotation.annotator_id,
            annotatorColor(index),
            useButton,
        );
        if (!hasSelectedPanel(annotation)) {
            previewMessage(body, "This annotation has no track-bearing panels.");
        } else if (!conflict.track_preview_available) {
            previewMessage(
                body,
                "Track preview unavailable: the pickle or plotting frequency is missing.",
            );
        } else {
            const url = new URL(
                "/api/adjudication/track-preview",
                window.location.origin,
            );
            url.searchParams.set("token_id", conflict.token_id);
            url.searchParams.set("annotator_id", annotation.annotator_id);
            previewImage(
                body,
                url.toString(),
                `Selected composite formant track for ${annotation.annotator_id}`,
            );
        }
        elements.trackComparisonGrid.append(card);
    });

    const proposal = currentAutomaticProposal();
    if (proposal) {
        const useButton = document.createElement("button");
        useButton.type = "button";
        useButton.className = "btn btn-primary btn-sm";
        useButton.textContent = "Use proposal";
        useButton.addEventListener("click", useAutomaticProposal);

        const title =
            `Proposal: ${displayResolutionType(proposal.metadata.resolution_type)}`;
        const {card, body} = previewCard(title, "#0d6efd", useButton);
        card.classList.add("is-proposal");
        previewImage(
            body,
            proposal.previewUrl,
            `${displayResolutionType(proposal.metadata.resolution_type)} proposal`,
        );
        const details = document.createElement("p");
        details.className = "proposal-details px-3 pb-3";
        details.textContent = proposal.metadata.summary;
        card.append(details);
        elements.trackComparisonGrid.append(card);
    }

    const draftCard = previewCard("Unsaved draft", DRAFT_COLOR);
    draftCard.card.dataset.previewKind = "draft";
    elements.trackComparisonGrid.append(draftCard.card);
    updateDraftPreviewCard();
}

function draftPreviewBody() {
    return elements.trackComparisonGrid.querySelector(
        '[data-preview-kind="draft"] .track-preview-body',
    );
}

function releaseDraftPreviewUrl() {
    if (state.draftPreviewUrl) {
        URL.revokeObjectURL(state.draftPreviewUrl);
        state.draftPreviewUrl = null;
    }
}

function updateDraftPreviewCard(message = null) {
    const body = draftPreviewBody();
    if (!body) {
        return;
    }
    const validation = state.currentConflict && currentDraft()
        ? draftValidation(currentDraft())
        : {valid: false, message: "Select a conflict to prepare a draft."};
    const draft = state.currentConflict ? currentDraft() : null;

    if (message) {
        previewMessage(body, message);
    } else if (!validation.valid) {
        previewMessage(body, validation.message);
    } else if (
        draft
        && ["average_tracks", "random_track"].includes(draft.resolution_type)
        && draft.automatic_preview_url
    ) {
        previewImage(
            body,
            draft.automatic_preview_url,
            `Unsaved ${displayResolutionType(draft.resolution_type)} draft`,
        );
    } else if (!state.currentConflict.track_preview_available) {
        previewMessage(
            body,
            "Track preview unavailable: the pickle or plotting frequency is missing.",
        );
    } else if (state.draftPreviewUrl) {
        previewImage(body, state.draftPreviewUrl, "Unsaved adjudication draft track");
    } else {
        previewMessage(body, "Rendering draft preview…");
    }
}

function scheduleDraftPreview(validation = updateDraftValidation()) {
    window.clearTimeout(state.previewTimer);
    state.previewRequestVersion += 1;
    releaseDraftPreviewUrl();

    const draft = currentDraft();
    if (
        validation.valid
        && draft
        && ["average_tracks", "random_track"].includes(draft.resolution_type)
    ) {
        updateDraftPreviewCard();
        return;
    }

    if (!validation.valid || !state.currentConflict?.track_preview_available) {
        updateDraftPreviewCard();
        return;
    }

    updateDraftPreviewCard("Rendering draft preview…");
    const requestVersion = state.previewRequestVersion;
    const tokenId = state.currentConflict.token_id;
    state.previewTimer = window.setTimeout(async () => {
        const draft = currentDraft();
        if (!draft || state.currentConflict?.token_id !== tokenId) {
            return;
        }
        const payload = {
            token_id: tokenId,
            panel_f1: draft.panel_f1,
            panel_f2: draft.panel_f2,
            panel_f3: draft.panel_f3,
            panel_f4: draft.panel_f4,
            needs_correction_f1: draft.needs_correction_f1,
            needs_correction_f2: draft.needs_correction_f2,
            needs_correction_f3: draft.needs_correction_f3,
            needs_correction_f4: draft.needs_correction_f4,
        };

        try {
            const blob = await apiPostImage(
                "/api/adjudication/draft-preview",
                payload,
            );
            if (
                requestVersion !== state.previewRequestVersion
                || state.currentConflict?.token_id !== tokenId
            ) {
                return;
            }
            state.draftPreviewUrl = URL.createObjectURL(blob);
            updateDraftPreviewCard();
            elements.draftStatus.textContent =
                "Draft preview updated. Nothing has been saved.";
            elements.draftStatus.className = "small text-success mt-3";
        } catch (error) {
            if (requestVersion !== state.previewRequestVersion) {
                return;
            }
            updateDraftPreviewCard(error.message);
            elements.draftStatus.textContent = `Preview error: ${error.message}`;
            elements.draftStatus.className = "small text-danger mt-3";
        }
    }, PREVIEW_DEBOUNCE_MS);
}


// ---------------------------------------------------------------------------
// Media and view switching
// ---------------------------------------------------------------------------

function renderMedia(conflict) {
    if (conflict.image_url) {
        elements.image.dataset.tokenId = conflict.token_id;
        elements.image.src = conflict.image_url;
        elements.imagePlaceholder.textContent = "Loading candidate image…";
        elements.imagePlaceholder.classList.remove("d-none");
        elements.imageWrapper.classList.add("d-none");
    } else {
        elements.image.removeAttribute("src");
        elements.imageWrapper.classList.add("d-none");
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

function setComparisonView(view) {
    state.activeView = view;
    const candidateActive = view === "candidate";
    elements.candidateView.classList.toggle("d-none", !candidateActive);
    elements.tracksView.classList.toggle("d-none", candidateActive);
    elements.candidateViewButton.className = candidateActive
        ? "btn btn-primary"
        : "btn btn-outline-primary";
    elements.tracksViewButton.className = candidateActive
        ? "btn btn-outline-primary"
        : "btn btn-primary";
    elements.candidateViewButton.setAttribute("aria-pressed", String(candidateActive));
    elements.tracksViewButton.setAttribute("aria-pressed", String(!candidateActive));
}


// ---------------------------------------------------------------------------
// Conflict-detail lifecycle
// ---------------------------------------------------------------------------

function renderConflict(conflict) {
    state.currentConflict = conflict;
    state.focusedFormant = 1;
    releaseDraftPreviewUrl();
    setDraftControlsEnabled(true);

    elements.tokenTitle.textContent =
        `${displayValue(conflict.phone)} ${displayValue(conflict.ipa)} — ${displayValue(conflict.word)}`;
    elements.tokenSubtitle.textContent =
        `${conflict.corpus} / ${conflict.batch} / index ${conflict.batch_index + 1}`;

    renderMetadata(conflict);
    renderAnnotations(conflict);
    renderMedia(conflict);
    renderAnnotatorLegend(conflict);
    writeDraftToControls();
    renderCandidateOverlays();
    renderUnplacedCorrectionWarning();
    renderAutomaticProposalStatus();
    renderTrackCards(conflict);
    scheduleDraftPreview(updateDraftValidation());
}

async function selectConflict(index) {
    const summary = state.conflicts[index];
    if (!summary) {
        return;
    }

    state.selectedIndex = index;
    state.detailRequestVersion += 1;
    const requestVersion = state.detailRequestVersion;
    renderConflictList();
    updateNavigation();
    showStatus(`Loading token ${summary.batch_index + 1}…`);

    try {
        const conflict = await apiGet("/api/adjudication/conflict", {
            token_id: summary.token_id,
        });
        if (requestVersion !== state.detailRequestVersion) {
            return;
        }
        renderConflict(conflict);
        hideStatus();
    } catch (error) {
        if (requestVersion === state.detailRequestVersion) {
            showStatus(error.message, "danger");
        }
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
        state.currentConflict = null;
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
    setDraftControlsEnabled(false);
    setComparisonView("candidate");
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


// ---------------------------------------------------------------------------
// Event registration
// ---------------------------------------------------------------------------

elements.batchSelect.addEventListener("change", loadSelectedBatch);
elements.previousButton.addEventListener("click", () => {
    selectConflict(state.selectedIndex - 1);
});
elements.nextButton.addEventListener("click", () => {
    selectConflict(state.selectedIndex + 1);
});
elements.candidateViewButton.addEventListener("click", () => {
    setComparisonView("candidate");
});
elements.tracksViewButton.addEventListener("click", () => {
    setComparisonView("tracks");
});
elements.resetDraftButton.addEventListener("click", resetDraft);
elements.averageTracksButton.addEventListener("click", () => {
    generateAutomaticProposal("average_tracks");
});
elements.randomTrackButton.addEventListener("click", () => {
    generateAutomaticProposal("random_track");
});
elements.useAutomaticProposalButton.addEventListener(
    "click",
    useAutomaticProposal,
);
elements.randomSeedInput.addEventListener(
    "input",
    invalidateAutomaticProposals,
);
elements.includeNeedsCorrectionInput.addEventListener(
    "change",
    invalidateAutomaticProposals,
);

for (const input of elements.draftPanelInputs) {
    input.addEventListener("focus", () => {
        setFocusedFormant(Number(input.dataset.formant));
        renderCandidateOverlays();
    });
    input.addEventListener("input", () => {
        readControlsIntoDraft();
        changeDraftToManualPanels();
        draftChanged();
    });
}
for (const input of elements.draftCorrectionInputs) {
    input.addEventListener("change", () => {
        readControlsIntoDraft();
        changeDraftToManualPanels();
        draftChanged();
    });
}
elements.draftNote.addEventListener("input", readControlsIntoDraft);

elements.image.addEventListener("load", () => {
    if (elements.image.dataset.tokenId !== state.currentConflict?.token_id) {
        return;
    }
    elements.imageWrapper.classList.remove("d-none");
    elements.imagePlaceholder.classList.add("d-none");
    renderCandidateOverlays();
});
elements.image.addEventListener("error", () => {
    elements.imageWrapper.classList.add("d-none");
    elements.imagePlaceholder.textContent = "Candidate image could not be loaded.";
    elements.imagePlaceholder.classList.remove("d-none");
});
window.addEventListener("beforeunload", () => {
    releaseDraftPreviewUrl();
    state.automaticProposals.forEach(releaseAutomaticProposal);
    state.drafts.forEach(releaseDraftAutomaticPreview);
});

initialize();
