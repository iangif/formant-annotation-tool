import { elements } from "./dom.js";
import { displayValue } from "./utils.js";
import { setControlsEnabled, fadeInSpectrogram, showToast } from "./ui.js";
import { setAllPanelInputs } from "./panels.js";
import { updateSpectrogramAspectRatio } from "./spectrogram.js";
import { resetFastTrackStateForToken } from "./fasttrack.js";

/**
 * Display the no-tokens-left state.
 */
export function renderNoTokensRemaining() {
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
export function renderToken(token) {
    const autoWinner = token.auto_winner_panel;
    resetFastTrackStateForToken(token);

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