/** Small DOM helpers. Text is always assigned with textContent, never parsed as HTML. */

/**
 * The element with this id, checked to be of `type` (HTMLElement by default).
 * A missing or different element throws at once, so a markup change cannot fail silently later.
 * @template {HTMLElement} [T=HTMLElement]
 * @param {string} id
 * @param {{new (): T, readonly name: string}} [type]
 * @returns {T}
 */
export function $(id, type) {
  const element = document.getElementById(id);
  const expected = type ?? HTMLElement;
  if (!(element instanceof expected)) throw new Error(`Expected #${id} to be ${expected.name}`);
  return /** @type {T} */ (element);
}

/**
 * Create an element holding plain text.
 * @template {keyof HTMLElementTagNameMap} K
 * @param {K} tag
 * @param {unknown} [text]
 * @param {string} [className]
 * @returns {HTMLElementTagNameMap[K]}
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
