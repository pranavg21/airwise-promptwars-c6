/** AirWise browser entry point: wires events. No frameworks, third-party scripts or inserted HTML. */
import { bindCitySearch, closeResults, placeLabel } from "./city-search.js";
import { $ } from "./dom.js";
import { conciseError, showNotice } from "./notice.js";
import { aiStatusLabel, askQuestion, copyBrief, generatePlan, resetPlan } from "./plan.js";
import { clearReadings, displaySnapshot, showLoading, showUnavailable } from "./readings.js";
import { EXAMPLE_CITIES, state } from "./state.js";
import { getJson } from "./transport.js";

function resetReadings() {
  state.readingsVersion++;
  state.snapshot = null;
  clearReadings();
  resetPlan();
}

async function loadSnapshot() {
  if (state.pendingCity) return;
  resetReadings();
  const version = state.readingsVersion;
  showLoading();
  try {
    const snapshot = await getJson("/api/air", { method: "POST", body: JSON.stringify(state.location) });
    if (version !== state.readingsVersion) return;
    state.snapshot = snapshot;
    displaySnapshot(snapshot);
  } catch (error) {
    if (version !== state.readingsVersion) return;
    showUnavailable();
    showNotice(
      `Live data could not be retrieved: ${conciseError(error)} No readings have been fabricated.`,
      true,
    );
  }
}

function setLocation(location) {
  state.searchVersion++;
  state.location = location;
  state.pendingCity = false;
  $("citySearch").value = location.name;
  $("chosenCity").textContent = `${location.name}, ${placeLabel(location)}`;
  closeResults();
  $("aqiCity").textContent = location.name.toUpperCase();
  showNotice("");
  void loadSnapshot();
}

function onSearchEdit() {
  state.pendingCity = true;
  resetReadings();
  $("aqiCity").textContent = "SELECT CITY";
  $("chosenCity").textContent = "Select a search result or city shortcut";
}

async function checkHealth() {
  try {
    const health = await getJson("/api/health");
    state.aiReady = health.ai_configured === true;
    $("aiStatus").textContent = aiStatusLabel();
  } catch {
    state.aiReady = false;
    $("aiStatus").textContent = "UNAVAILABLE";
  }
}

function bindPlanEvents() {
  const form = $("settingsForm");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void generatePlan();
  });
  form.addEventListener("change", (event) => {
    if (event.target.id === "citySearch") return;
    resetPlan();
    showNotice("Preferences changed. Build a plan for the new settings.");
  });
  $("recommendations").addEventListener("click", (event) => {
    if (event.target.closest("#emptyGenerate")) void generatePlan();
  });
  $("askForm").addEventListener("submit", (event) => void askQuestion(event));
  for (const button of document.querySelectorAll(".sample-question")) {
    button.addEventListener("click", () => {
      $("question").value = button.textContent.trim();
      $("question").focus();
    });
  }
}

function bindPageEvents() {
  for (const button of document.querySelectorAll("[data-city]")) {
    button.addEventListener("click", () => setLocation(EXAMPLE_CITIES[button.dataset.city]));
  }
  $("aboutBtn").addEventListener("click", () => $("methodology").scrollIntoView({ behavior: "smooth" }));
  $("refreshBtn").addEventListener("click", () => void loadSnapshot());
  $("copyBtn").addEventListener("click", () => void copyBrief());
  $("printBtn").addEventListener("click", () => window.print());
}

bindCitySearch({ onSelect: setLocation, onEdit: onSearchEdit });
bindPlanEvents();
bindPageEvents();
setLocation(EXAMPLE_CITIES.delhi);
void checkHealth();
