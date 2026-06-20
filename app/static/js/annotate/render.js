import { elements } from "./dom.js";
import { displayValue } from "./utils.js";
import { state } from "./state.js";
import { setControlsEnabled, fadeInSpectrogram, showToast } from "./ui.js";
import { setAllPanelInputs, setPanelInputsFromAnnotation } from "./panels.js";
import { updateSpectrogramAspectRatio } from "./spectrogram.js";
import { resetFastTrackStateForToken } from "./fasttrack.js";
import { prefillNote, renderNoteDropdown, renderTokenNoteCue } from "./notes.js";

function setStatusBadge(label, className) {
    elements.tokenStatusBadge.textContent = label;
    elements.tokenStatusBadge.className = `badge ${className}`;
}

function clearTokenDisplay(message) {
    elements.tokenIdLabel.textContent = "No token loaded";
    elements.emptyState.classList.remove("d-none");
    elements.emptyState.textContent = message;
    elements.spectrogramWrapper.classList.add("d-none");
    elements.spectrogramImage.classList.add("d-none");

    elements.metaWord.textContent = "—";
    elements.metaVowel.textContent = "—";
    elements.metaCorpus.textContent = "—";
    elements.metaSpeaker.textContent = "—";
    elements.metaContext.textContent = "—";
    elements.metaDuration.textContent = "—";
    elements.metaAutoWinner.textContent = "—";
    elements.metaAlignmentCommentLabel.classList.add("d-none");
    elements.metaAlignmentComment.classList.add("d-none");
    elements.metaAlignmentComment.textContent = "—";

    elements.audioPlayer.classList.add("d-none");
    elements.audioPlayer.removeAttribute("src");

    setAllPanelInputs("");
    elements.notes.value = "";
    elements.tokenNoteCue.classList.add("d-none");
}

export function renderNoAssignedBatches() {
    clearTokenDisplay("No local batches are assigned to this annotator. Run the sync scripts first.");
    elements.progressLabel.textContent = "No assigned batches.";
    elements.batchPositionLabel.textContent = "—";
    elements.batchMenuBtn.textContent = "No batches";
    elements.batchMenuBtn.disabled = true;
    setStatusBadge("No batch", "text-bg-secondary");
}

export function renderBatchMenu() {
    elements.batchMenu.innerHTML = "";
    elements.batchMenuBtn.disabled = state.batches.length === 0;

    if (state.batches.length === 0) {
        elements.batchMenuBtn.textContent = "No batches";
        return;
    }

    const currentBatch = state.batches.find((batch) => batch.id === state.currentBatchId);
    elements.batchMenuBtn.textContent = currentBatch
        ? `${currentBatch.corpus} / ${currentBatch.name}`
        : "Choose batch";

    renderNoteDropdown();

    for (const batch of state.batches) {
        const item = document.createElement("li");
        const button = document.createElement("button");

        button.type = "button";
        button.className = "dropdown-item batch-menu-item";
        button.dataset.batchId = String(batch.id);

        if (batch.id === state.currentBatchId) {
            button.classList.add("active");
        }

        button.innerHTML = `
            <span class="d-block fw-semibold">${batch.corpus} / ${batch.name}</span>
            <span class="d-block small opacity-75">
                ${batch.completed_count} / ${batch.total_count} complete
                (${batch.remaining_count} remaining)
            </span>
        `;

        item.appendChild(button);
        elements.batchMenu.appendChild(item);
    }
}

export function renderBatchProgress() {
    const progress = state.currentBatchProgress;

    if (!progress) {
        elements.progressLabel.textContent = "No batch loaded.";
        elements.batchPositionLabel.textContent = "—";
        return;
    }

    elements.progressLabel.textContent =
        `${progress.corpus} / ${progress.name}: ` +
        `${progress.completed_count} / ${progress.total_count} complete ` +
        `(${progress.remaining_count} remaining)`;

    if (state.currentBatchIndex === null) {
        elements.batchPositionLabel.textContent = "—";
    } else {
        elements.batchPositionLabel.textContent =
            `Token index ${state.currentBatchIndex + 1} of ${progress.total_count}`;
    }
}

export function renderTokenStatus(token) {
    const latest = token.latest_annotation;

    if (!latest) {
        setStatusBadge("Unannotated", "text-bg-secondary");
        return;
    }

    if (latest.decision === "bad_token") {
        setStatusBadge("Bad", "text-bg-danger");
        return;
    }

    if (latest.decision === "needs_correction") {
        setStatusBadge("Needs correction", "text-bg-warning");
        return;
    }

    setStatusBadge("Annotated", "text-bg-success");
}

export function prefillAnnotationFields(token) {
    const latest = token.latest_annotation;

    if (latest) {
        setPanelInputsFromAnnotation(latest);
        prefillNote(token);
        return;
    }

    setAllPanelInputs(token.auto_winner_panel);
    prefillNote(token);
}

export function renderToken(token) {
    const autoWinner = token.auto_winner_panel;
    resetFastTrackStateForToken(token);
    state.displayedAutoWinnerPanel = token.auto_winner_panel;

    elements.tokenIdLabel.textContent = token.token_id;

    elements.metaWord.textContent = displayValue(token.word);
    elements.metaVowel.textContent = displayValue(token.ipa ?? token.phone);
    elements.metaCorpus.textContent = displayValue(token.corpus);
    elements.metaSpeaker.textContent = displayValue(token.speaker);

    elements.metaContext.textContent =
        `${displayValue(token.previous_phone)} _ ${displayValue(token.following_phone)}`;

    elements.metaDuration.textContent =
        token.duration_ms === null || token.duration_ms === undefined
        ? "—"
        : `${token.duration_ms} ms`;

    elements.metaAutoWinner.textContent = autoWinner;

    if (token.alignment_comment) {
        elements.metaAlignmentComment.textContent = token.alignment_comment;
        elements.metaAlignmentCommentLabel.classList.remove("d-none");
        elements.metaAlignmentComment.classList.remove("d-none");
    } else {
        elements.metaAlignmentComment.textContent = "—";
        elements.metaAlignmentCommentLabel.classList.add("d-none");
        elements.metaAlignmentComment.classList.add("d-none");
    }

    prefillAnnotationFields(token);
    renderTokenStatus(token);
    renderTokenNoteCue(token);
    renderBatchProgress();
    renderNoteDropdown();

    elements.spectrogramImage.onload = () => {
        updateSpectrogramAspectRatio();
        fadeInSpectrogram();
    };

    elements.spectrogramWrapper.classList.add("is-transitioning");
    elements.spectrogramImage.classList.remove("d-none");
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

export function renderNoTokensRemaining() {
    clearTokenDisplay("No remaining assigned tokens.");
    setStatusBadge("Complete", "text-bg-success");
    setControlsEnabled(false);
    showToast("All assigned tokens have been annotated.", "success");
}
