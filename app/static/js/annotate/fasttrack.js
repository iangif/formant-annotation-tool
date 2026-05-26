import { elements } from "./dom.js";
import { state } from "./state.js";
import { showToast, setControlsEnabled } from "./ui.js";

function setPlaceholder(input, value) {
    input.placeholder = value === null || value === undefined ? "" : String(value);
}

export function resetFastTrackStateForToken(token) {
    state.displayedImageSource = "original";
    state.alternateImageUrl = null;
    state.alternateFastTrackParams = null;

    elements.fasttrackMinMaxFormant.value = "";
    elements.fasttrackMaxMaxFormant.value = "";
    elements.fasttrackNFormants.value = "";

    setPlaceholder(elements.fasttrackMinMaxFormant, token.min_max_formant);
    setPlaceholder(elements.fasttrackMaxMaxFormant, token.max_max_formant);
    setPlaceholder(elements.fasttrackNFormants, token.n_formants);
}

function readNumberOrPlaceholder(input) {
    const rawValue = input.value.trim() || input.placeholder.trim();

    if (rawValue === "") {
        return null;
    }

    const value = Number(rawValue);

    if (!Number.isFinite(value)) {
        return null;
    }

    return value;
}

export function readFastTrackParams() {
    const minMaxFormant = readNumberOrPlaceholder(elements.fasttrackMinMaxFormant);
    const maxMaxFormant = readNumberOrPlaceholder(elements.fasttrackMaxMaxFormant);
    const nFormants = readNumberOrPlaceholder(elements.fasttrackNFormants);

    if (
        minMaxFormant === null ||
        maxMaxFormant === null ||
        nFormants === null
    ) {
        throw new Error("FastTrack requires min max formant, max max formant, and n formants.");
    }

    return {
        min_max_formant: minMaxFormant,
        max_max_formant: maxMaxFormant,
        n_formants: Number.parseInt(nFormants, 10),
    };
}

export async function generateFastTrackAlternative() {
    if (!state.currentToken) {
        throw new Error("No token is currently loaded.");
    }

    const params = readFastTrackParams();

    setControlsEnabled(false);

    try {
        const response = await fetch(
            `/api/tokens/${encodeURIComponent(state.currentToken.id)}/fasttrack`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(params),
            }
        );

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(data?.detail || "Failed to generate FastTrack alternative.");
        }

        state.displayedImageSource = "alternate";
        state.alternateImageUrl = data.alternate_image_url;
        state.alternateFastTrackParams = params;

        elements.spectrogramImage.src = `${data.alternate_image_url}?t=${Date.now()}`;

        showToast(data.message || "Generated FastTrack alternative.", "success");
    
    } finally {
        setControlsEnabled(true);
    }
}

export function restoreOriginalImage() {
    if (!state.currentToken) {
        return;
    }

    state.displayedImageSource = "original";

    elements.spectrogramImage.src = `${state.currentToken.image_url}?t=${Date.now()}`;

    showToast("Restored original spectrogram.", "info");
}

export function registerFastTrackEvents() {
    elements.generateFasttrackBtn.addEventListener("click", async () => {
        try {
            await generateFastTrackAlternative();
        } catch (error) {
            showToast(error.message, "danger");
            setControlsEnabled(true);
        }
    });

    elements.restoreOriginalBtn.addEventListener("click", () => {
        restoreOriginalImage();
    });
}