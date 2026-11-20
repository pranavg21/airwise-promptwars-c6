/** The current-air panel, metric cards and 24-hour outlook. */
import { renderChart, renderHourTable } from "./chart.js";
import { $, clock, safeNumber } from "./dom.js";
/** @import { Snapshot } from "./types" */

const READING_IDS = ["aqiValue", "pm25", "pm10", "bestAQI", "aqiTime", "bestTime"];

/**
 * Category label from the server (airwise/aqi.py); `key` selects its colour in CSS.
 * @param {string} label
 * @param {string} [key]
 */
function setCategory(label, key) {
  const category = $("aqiCategory");
  category.textContent = label;
  if (key) category.dataset.band = key;
  else delete category.dataset.band;
}

export function clearReadings() {
  for (const id of READING_IDS) $(id).textContent = "—";
  $("feedStatus").textContent = "AWAITING DATA";
  setCategory("Awaiting forecast");
  $("dataStamp").textContent = "No forecast loaded";
  $("chart").replaceChildren();
  $("hourlyTable").replaceChildren();
}

export function showLoading() {
  $("aqiValue").textContent = "···";
  setCategory("Connecting to air model...");
}

export function showUnavailable() {
  $("aqiValue").textContent = "—";
  setCategory("Forecast unavailable");
  $("feedStatus").textContent = "DATA UNAVAILABLE";
}

/** @param {Snapshot} snapshot */
function renderCurrent(snapshot) {
  const time = `${clock(snapshot.model_time)} (${snapshot.timezone})`;
  $("aqiValue").textContent = safeNumber(snapshot.us_aqi);
  $("feedStatus").textContent = "LATEST MODEL ESTIMATE";
  setCategory(snapshot.category, snapshot.category_key);
  $("aqiTime").textContent = `${clock(snapshot.model_time)} · ${snapshot.timezone} local`;
  $("pm25").textContent = safeNumber(snapshot.pm2_5, 1);
  $("pm10").textContent = safeNumber(snapshot.pm10, 1);
  $("aqiCity").textContent = snapshot.location.name.toUpperCase();
  $("dataStamp").textContent =
    `Open-Meteo/CAMS model · ${time}; fetched ${new Date(snapshot.retrieved_at).toLocaleString()}`;
}

/** The server decides which hours form the outlook (airwise/forecast.py); the browser only draws them. */
/** @param {Snapshot} snapshot */
function renderOutlook(snapshot) {
  const hours = snapshot.outlook ?? [];
  const lowest = snapshot.outlook_lowest;
  $("bestAQI").textContent = lowest ? safeNumber(lowest.us_aqi) : "—";
  $("bestTime").textContent = lowest
    ? `${clock(lowest.time)} local · not necessarily safe`
    : "No valid 24-hour forecast";
  renderChart($("chart"), hours);
  renderHourTable($("hourlyTable"), hours);
}

/**
 * Render a forecast snapshot from /api/air or /api/plan.
 * @param {Snapshot} snapshot
 */
export function displaySnapshot(snapshot) {
  renderCurrent(snapshot);
  renderOutlook(snapshot);
}
