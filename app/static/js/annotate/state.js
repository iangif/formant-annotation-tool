export const state = {
    currentToken: null,
    isSaving: false,
    hoveredPanel: null,

    batches: [],
    currentBatchId: null,
    currentBatchProgress: null,
    currentBatchTokens: [],
    currentBatchIndex: null,
    skippedIndices: new Set(),

    displayedImageSource: "original",
    displayedAutoWinnerPanel: null,

    alternateImageUrl: null,
    alternateFastTrackParams: null,
    fasttrackCacheKey: null,
};
