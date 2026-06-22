import { elements, annotatorId } from "./dom.js";
import { state } from "./state.js";
import { fetchJson, loadTokenAtIndex } from "./api.js";
import { showToast } from "./ui.js";

function currentNoteText() {
    return elements.notes.value.trim();
}

function setNoteSavingLabel(text) {
    elements.noteSaveIndicator.textContent = text;
}

export function tokenHasNote(token) {
    return Boolean(token.latest_note?.note?.trim() || token.has_note);
}

export function renderTokenNoteCue(token) {
    const hasNote = tokenHasNote(token);
    elements.tokenNoteCue.classList.toggle("d-none", !hasNote);
    elements.tokenNoteCue.title = hasNote ? "This token has a saved note" : "";
}

export function renderNoteDropdown() {
    elements.noteDropdownMenu.innerHTML = "";

    const notedTokens = state.currentBatchTokens
        .filter((token) => token.has_note && token.note && token.note.trim())
        .sort((a, b) => a.batch_index - b.batch_index);

    elements.noteDropdownBtn.disabled = notedTokens.length === 0;
    elements.noteDropdownBtn.textContent = notedTokens.length === 0
        ? "Notes"
        : `Notes (${notedTokens.length})`;

    if (notedTokens.length === 0) {
        const item = document.createElement("li");
        item.innerHTML = `<span class="dropdown-item-text small text-muted">No saved notes in this batch.</span>`;
        elements.noteDropdownMenu.appendChild(item);
        return;
    }

    for (const token of notedTokens) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        const preview = token.note.trim().replace(/\s+/g, " ");

        const title = document.createElement("span");
        const previewLine = document.createElement("span");

        button.type = "button";
        button.className = "dropdown-item note-menu-item";
        button.dataset.batchIndex = String(token.batch_index);

        title.className = "d-block fw-semibold";
        title.textContent = `${token.batch_index + 1} — ${token.word || token.phone || token.file_stem}`;

        previewLine.className = "d-block small text-muted text-truncate";
        previewLine.textContent = preview;

        button.append(title, previewLine);
        item.appendChild(button);
        elements.noteDropdownMenu.appendChild(item);
    }
}

export function prefillNote(token) {
    const noteText = token.latest_note?.note || "";
    elements.notes.value = noteText;
    state.lastSavedNote = noteText.trim();
    setNoteSavingLabel("");
    renderTokenNoteCue(token);
}

function updateLoadedTokenNote(note) {
    if (!state.currentToken || state.currentToken.token_id !== note.token_id) {
        return;
    }

    state.currentToken.latest_note = note;
    state.currentToken.has_note = Boolean(note.note.trim());
    renderTokenNoteCue(state.currentToken);
}

function updateCurrentSummaryNote(note) {
    const summary = state.currentBatchTokens.find(
        (token) => token.token_id === note.token_id
    );

    if (!summary) {
        return;
    }

    summary.note = note.note;
    summary.has_note = Boolean(note.note.trim());
    renderNoteDropdown();
}

export function flashNoteSaved() {
    elements.notes.classList.remove("note-saved-glow");
    // Force a reflow so repeated saves restart the animation.
    void elements.notes.offsetWidth;
    elements.notes.classList.add("note-saved-glow");
    setNoteSavingLabel("Saved");

    window.setTimeout(() => {
        elements.notes.classList.remove("note-saved-glow");
        setNoteSavingLabel("");
    }, 900);
}

export async function saveCurrentNote({ force = false } = {}) {
    if (!state.currentToken) {
        return null;
    }

    const noteText = currentNoteText();

    if (!force && noteText === state.lastSavedNote) {
        return null;
    }

    setNoteSavingLabel("Saving...");

    const note = await fetchJson(
        "/api/notes",
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                token_id: state.currentToken.token_id,
                annotator_id: annotatorId,
                note: noteText,
            }),
        },
        "Failed to save note."
    );

    state.lastSavedNote = note.note.trim();
    updateLoadedTokenNote(note);
    updateCurrentSummaryNote(note);
    flashNoteSaved();
    return note;
}

export async function saveCurrentNoteAndBlur() {
    try {
        await saveCurrentNote();
    } catch (error) {
        showToast(error.message, "danger");
    } finally {
        elements.notes.blur();
    }
}

export function registerNoteEvents() {
    elements.notes.addEventListener("focus", () => {
        setNoteSavingLabel("");
    });

    elements.notes.addEventListener("blur", () => {
        saveCurrentNote().catch((error) => showToast(error.message, "danger"));
    });

    elements.notes.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        event.preventDefault();
        saveCurrentNoteAndBlur();
    });

    elements.noteDropdownMenu.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-batch-index]");

        if (!button) {
            return;
        }

        const batchIndex = Number.parseInt(button.dataset.batchIndex, 10);

        if (!Number.isInteger(batchIndex)) {
            return;
        }

        try {
            const direction = batchIndex > state.currentBatchIndex ? 1 : -1;
            await loadTokenAtIndex(batchIndex, direction);
        } catch (error) {
            showToast(error.message, "danger");
        }
    });
}
