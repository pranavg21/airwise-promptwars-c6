/** Same-origin JSON requests with a deadline; the browser never contacts third-party hosts. */

// The server finishes or abandons AI work within 22 s (airwise/config.py REQUEST_BUDGET_S).
const REQUEST_TIMEOUT_MS = 25_000;
const MAX_ERROR_CHARS = 250;
const API_PATH = /^\/api\/[a-z]+(?:\?[a-z0-9=&%+._-]+)?$/i;

/**
 * The server's error message for a failed response, or its HTTP status.
 * @param {Response} response
 * @returns {Promise<string>}
 */
async function errorMessage(response) {
  try {
    const body = await response.json();
    const message = body.detail || body.error;
    if (typeof message === "string") return message.slice(0, MAX_ERROR_CHARS);
  } catch {
    // No JSON body: fall back to the status code.
  }
  return `HTTP ${response.status}`;
}

/**
 * Fetch JSON from this app's API. Rejects with a readable message on error or timeout.
 * @param {string} path An /api/ path, optionally with a simple query string.
 * @param {RequestInit} [options]
 * @returns {Promise<any>}
 */
export async function getJson(path, options = {}) {
  if (!API_PATH.test(path)) throw new Error("Invalid API path");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(path, {
      ...options,
      headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
      cache: "no-store",
      credentials: "same-origin",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(await errorMessage(response));
    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out. Retry when connectivity improves.", { cause: error });
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
