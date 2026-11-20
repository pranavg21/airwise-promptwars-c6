/** Small DOM helpers. Text is always assigned with textContent, never parsed as HTML. */

/**
 * @param {string} id
 * @returns {HTMLElement}
 */
export const $ = (id) => document.getElementById(id);

/**
 * Create an element holding plain text.
 * @param {string} tag
 * @param {unknown} [text]
 * @param {string} [className]
 * @returns {HTMLElement}
 */
export function node(tag, text = "", className = "") {
  const element = document.createElement(tag);
  element.textContent = String(text);
  if (className) element.className = className;
  return element;
}

/**
 * A finite number with fixed decimals, or an em dash when the value is missing.
 * @param {unknown} value
 * @param {number} [decimals]
 * @returns {string}
 */
export function safeNumber(value, decimals = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(decimals) : "—";
}

/**
 * "MM-DD · HH:MM" from an ISO local timestamp such as 2026-11-20T08:00.
 * @param {unknown} timestamp
 * @returns {string}
 */
export function clock(timestamp) {
  return typeof timestamp === "string" && timestamp.length >= 16
    ? `${timestamp.slice(5, 10)} · ${timestamp.slice(11, 16)}`
    : "Unavailable";
}
