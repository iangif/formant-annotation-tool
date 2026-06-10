export const state = {
    currentToken: null,
    isSaving: false,
    hoveredPanel: null,

    batches: [],
    currentBatchId: null,
    currentBatchProgress: null,
    currentBatchTokens: [],
    currentBatchIndex: null,

    autoAdvanceEnabled: true,
    hotkeysPanelOpen: false,
    navigationDirection: 0,

    displayedImageSource: "original",
    displayedAutoWinnerPanel: null,

    alternateImageUrl: null,
    alternateFastTrackParams: null,
    fasttrackCacheKey: null,
};
