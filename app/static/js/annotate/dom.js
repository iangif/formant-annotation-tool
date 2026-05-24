export const annotatorId = document
    .getElementById("annotator-id")
    .textContent
    .trim();

export const elements = {
    progressLabel: document.getElementById("progress-label"),
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
    openPraatBtn: document.getElementById("open-praat-btn"),
    closePraatBtn: document.getElementById("close-praat-btn"),
};