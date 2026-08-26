export const annotatorId = document
    .getElementById("annotator-id")
    .textContent
    .trim();

export const elements = {
    progressLabel: document.getElementById("progress-label"),
    batchPositionLabel: document.getElementById("batch-position-label"),
    toastContainer: document.getElementById("toast-container"),
    toastTemplate: document.getElementById("toast-template"),

    mainLayout: document.getElementById("main-layout"),
    resizeHandle: document.getElementById("resize-handle"),

    emptyState: document.getElementById("empty-state"),
    spectrogramWrapper: document.getElementById("spectrogram-wrapper"),
    spectrogramImage: document.getElementById("spectrogram-image"),
    panelHoverOverlay: document.getElementById("panel-hover-overlay"),
    panelHoverLabel: document.getElementById("panel-hover-label"),

    tokenIdLabel: document.getElementById("token-id-label"),
    tokenStatusBadge: document.getElementById("token-status-badge"),
    tokenNoteCue: document.getElementById("token-note-cue"),

    metaWord: document.getElementById("meta-word"),
    metaVowel: document.getElementById("meta-vowel"),
    metaCorpus: document.getElementById("meta-corpus"),
    metaSpeaker: document.getElementById("meta-speaker"),
    metaGender: document.getElementById("meta-gender"),
    metaContext: document.getElementById("meta-context"),
    metaDuration: document.getElementById("meta-duration"),
    metaAutoWinner: document.getElementById("meta-auto-winner"),
    metaAlignmentCommentLabel: document.getElementById("meta-alignment-comment-label"),
    metaAlignmentComment: document.getElementById("meta-alignment-comment"),

    audioPlayer: document.getElementById("audio-player"),

    panelF1: document.getElementById("panel-f1"),
    panelF2: document.getElementById("panel-f2"),
    panelF3: document.getElementById("panel-f3"),
    panelF4: document.getElementById("panel-f4"),
    needsCorrectionF1: document.getElementById("needs-correction-f1"),
    needsCorrectionF2: document.getElementById("needs-correction-f2"),
    needsCorrectionF3: document.getElementById("needs-correction-f3"),
    needsCorrectionF4: document.getElementById("needs-correction-f4"),

    notes: document.getElementById("notes"),
    noteSaveIndicator: document.getElementById("note-save-indicator"),

    batchMenuBtn: document.getElementById("batch-menu-btn"),
    batchMenu: document.getElementById("batch-menu"),
    demoBatchBtn: document.getElementById("demo-batch-btn"),
    jumpTokenBtn: document.getElementById("jump-token-btn"),
    batchIndexInput: document.getElementById("batch-index-input"),
    noteDropdownBtn: document.getElementById("note-dropdown-btn"),
    noteDropdownMenu: document.getElementById("note-dropdown-menu"),
    autoAdvanceToggle: document.getElementById("auto-advance-toggle"),
    hotkeysBtn: document.getElementById("hotkeys-btn"),
    hotkeysBackdrop: document.getElementById("hotkeys-backdrop"),
    hotkeysPanel: document.getElementById("hotkeys-panel"),
    closeHotkeysBtn: document.getElementById("close-hotkeys-btn"),

    reloadTokenBtn: document.getElementById("reload-token-btn"),
    openPraatBtn: document.getElementById("open-praat-btn"),
    closePraatBtn: document.getElementById("close-praat-btn"),

    fasttrackMenuBtn: document.getElementById("fasttrack-menu-btn"),
    fasttrackMinMaxFormant: document.getElementById("fasttrack-min-max-formant"),
    fasttrackMaxMaxFormant: document.getElementById("fasttrack-max-max-formant"),
    fasttrackNFormants: document.getElementById("fasttrack-n-formants"),
    generateFasttrackBtn: document.getElementById("generate-fasttrack-btn"),
    restoreOriginalBtn: document.getElementById("restore-original-btn"),
};
