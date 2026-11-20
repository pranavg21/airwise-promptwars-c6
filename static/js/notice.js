/** The page-level status message. */
import { $ } from "./dom.js";

/**
 * @param {unknown} error
 * @returns {string}
 */
export function conciseError(error) {
  return error instanceof Error ? error.message : "Something went wrong. Please retry.";
}

/**
 * Show a status message; an empty message hides it. Errors use the warning tone.
 * @param {string} message
 * @param {boolean} [isError]
 */
export function showNotice(message, isError = false) {
  const notice = $("notice");
  notice.textContent = message;
  notice.hidden = !message;
  notice.dataset.tone = isError ? "error" : "ok";
}
