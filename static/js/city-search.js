/**
 * City search. Suggestions appear only after an explicit search (Enter or the arrow button);
 * each suggestion is a button, and the search button owns the expanded state.
 */
import { $, node } from "./dom.js";
import { conciseError, showNotice } from "./notice.js";
import { state } from "./state.js";
import { getJson } from "./transport.js";

const MIN_QUERY_LENGTH = 3;

function setResultsOpen(open) {
  $("cityResults").hidden = !open;
  $("citySearchBtn").setAttribute("aria-expanded", String(open));
}

function announce(message) {
  $("cityStatus").textContent = message;
}

/** Close the suggestions and cancel any search that has not answered yet. */
export function dismissResults() {
  state.searchVersion++;
  setResultsOpen(false);
}

/**
 * The geocoding request for a typed city name. URLSearchParams escapes apostrophes and brackets,
 * which encodeURIComponent leaves as they are (for example "St. John's" or "L'Aquila").
 * @param {string} query
 * @returns {string}
 */
export function cityQueryPath(query) {
  return `/api/geo?${new URLSearchParams({ q: query })}`;
}

/** @param {{region?: string, country: string}} city */
export function placeLabel(city) {
  return `${city.region ? `${city.region}, ` : ""}${city.country}`;
}

function resultButton(city, onSelect) {
  const button = node("button", city.name);
  button.type = "button";
  button.append(node("small", placeLabel(city)));
  button.addEventListener("click", () => {
    onSelect(city);
    $("citySearch").focus();
    announce(`Selected ${$("chosenCity").textContent}.`);
  });
  return button;
}

function showResults(cities, onSelect) {
  const list = $("cityResults");
  list.replaceChildren();
  if (!cities.length) {
    list.append(node("p", "No matching city found. Try a longer name.", "field-help"));
    announce("No matching city found.");
    return;
  }
  for (const city of cities) list.append(resultButton(city, onSelect));
  announce(
    `${cities.length} matching ${cities.length === 1 ? "city" : "cities"}. Press Down Arrow to choose.`,
  );
}

async function searchCity(onSelect) {
  const query = $("citySearch").value.trim();
  if (query.length < MIN_QUERY_LENGTH) {
    setResultsOpen(false);
    showNotice("Type at least 3 characters to search a city.", true);
    return;
  }
  const version = ++state.searchVersion;
  setResultsOpen(true);
  $("cityResults").replaceChildren(node("p", "Searching cities...", "field-help"));
  announce("Searching cities...");
  try {
    const payload = await getJson(cityQueryPath(query));
    if (version === state.searchVersion) showResults(payload.results, onSelect);
  } catch (error) {
    if (version !== state.searchVersion) return;
    $("cityResults").replaceChildren(node("p", conciseError(error), "field-help"));
    announce(conciseError(error));
  }
}

function onSearchKey(event, onSelect) {
  if (event.key === "Enter") {
    event.preventDefault();
    void searchCity(onSelect);
  } else if (event.key === "ArrowDown" && !$("cityResults").hidden) {
    event.preventDefault();
    $("cityResults").querySelector("button")?.focus();
  } else if (event.key === "Escape") {
    dismissResults();
  }
}

function onResultsKey(event) {
  const buttons = [...$("cityResults").querySelectorAll("button")];
  const position = buttons.indexOf(document.activeElement);
  if (event.key === "ArrowDown") {
    event.preventDefault();
    buttons[Math.min(position + 1, buttons.length - 1)]?.focus();
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    (position === 0 ? $("citySearch") : buttons[Math.max(0, position - 1)])?.focus();
  } else if (event.key === "Escape") {
    dismissResults();
    $("citySearch").focus();
  }
}

/**
 * Wire the search field, its button and the suggestion list.
 * @param {{onSelect: (city: object) => void, onEdit: () => void}} handlers
 *   onSelect runs when a suggestion is chosen; onEdit when the typed text changes.
 */
export function bindCitySearch({ onSelect, onEdit }) {
  const search = $("citySearch");
  $("citySearchBtn").addEventListener("click", () => void searchCity(onSelect));
  search.addEventListener("input", () => {
    state.searchVersion++;
    setResultsOpen(false);
    onEdit();
  });
  search.addEventListener("keydown", (event) => onSearchKey(event, onSelect));
  $("cityResults").addEventListener("keydown", onResultsKey);
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".search-wrap") && !event.target.closest(".city-results")) dismissResults();
  });
}

/** Close the suggestions after a city is chosen another way (for example a shortcut). */
export function closeResults() {
  setResultsOpen(false);
}
