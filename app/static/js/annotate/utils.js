/**
 * Simple async delay utility.
 */
export function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Clamps value between min and max.
 */
export function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

/**
 * Convert null, undefined, or empty values into a display fallback.
 */
export function displayValue(value, fallback = "—") {
    if (value === null || value === undefined || value === "") {
        return fallback;
    }

    return value;
}