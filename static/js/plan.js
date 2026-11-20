/** Building the plan, asking follow-up questions and sharing the community brief. */
import { communityBrief } from "./brief.js";
import { $, node } from "./dom.js";
import { conciseError, showNotice } from "./notice.js";
import { renderAi, renderAnswer, renderAnswerFallback, renderRecommendations } from "./plan-view.js";
import { displaySnapshot } from "./readings.js";
import { state } from "./state.js";
import { getJson } from "./transport.js";
/** @import { AskResponse, PlanResponse } from "./types" */

const MAX_OUTDOOR_MINUTES = 480;
const MIN_QUESTION_LENGTH = 5;
const PLAN_PANELS = [
  "planSubtitle",
  "recommendations",
  "swaps",
  "shiftResult",
  "traceList",
  "aiContent",
  "askAnswer",
];
// Module scripts run after parsing, so the panels' initial content can be captured here.
const initialPanels = new Map(PLAN_PANELS.map((id) => [id, $(id).cloneNode(true)]));

export function aiStatusLabel() {
  // A key is set; whether Gemini has quota left is only known when a request is made.
  return state.aiReady ? "CONFIGURED · OPT IN" : "NOT CONFIGURED";
}

/** Clear the plan and invalidate any plan or answer still in flight. */
export function resetPlan() {
  state.planVersion++;
  state.policy = null;
  for (const [id, template] of initialPanels) {
    $(id).replaceChildren(...Array.from(template.childNodes, (child) => child.cloneNode(true)));
  }
  $("copyBtn", HTMLButtonElement).disabled = $("printBtn", HTMLButtonElement).disabled = true;
  $("aiStatus").textContent = aiStatusLabel();
}

/** @param {string} id */
const checked = (id) => $(id, HTMLInputElement).checked;
/** @param {string} id */
const chosen = (id) => $(id, HTMLSelectElement).value;

/** The household profile as the API expects it (airwise/models.py Profile). */
function readProfile() {
  const minutes = Number($("outdoorMin", HTMLInputElement).value) || 0;
  /** @type {NodeListOf<HTMLInputElement>} */
  const priorities = document.querySelectorAll(".priority:checked");
  return {
    persona: chosen("persona"),
    children: checked("children"),
    older_adult: checked("older"),
    respiratory_sensitivity: checked("respiratory"),
    outdoor_minutes: Math.max(0, Math.min(MAX_OUTDOOR_MINUTES, minutes)),
    start_hour: Number(chosen("startHour")),
    budget: chosen("budget"),
    priorities: [...priorities].map((box) => box.value),
    language: chosen("language"),
  };
}

/** @param {Record<string, unknown>} [extra] Fields that add to or override the defaults. */
function requestBody(extra = {}) {
  return { location: state.location, profile: readProfile(), ai_consent: checked("aiConsent"), ...extra };
}

/**
 * @param {HTMLButtonElement} button
 * @param {boolean} busy
 * @param {string} label
 */
function setBusy(button, busy, label) {
  button.disabled = busy;
  if (button.firstElementChild) button.firstElementChild.textContent = label;
}

/** @param {PlanResponse} data */
function showPlan(data) {
  state.readingsVersion++;
  state.snapshot = data.snapshot;
  state.policy = data.policy;
  displaySnapshot(data.snapshot);
  renderRecommendations(data.policy);
  renderAi(data);
  const aiNote =
    data.ai_status === "generated"
      ? "Gemini personalization generated."
      : "Source-backed recommendations ready.";
  showNotice(`Plan refreshed from modeled air data. ${aiNote}`);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  $("recommendations").focus({ preventScroll: true });
  $("recommendations").scrollIntoView({ behavior: reducedMotion ? "instant" : "smooth", block: "start" });
}

/**
 * Request a plan for the current city and settings; late responses for old settings are dropped.
 * @param {boolean} [withAi] Ask for a Gemini briefing; defaults to the consent checkbox.
 */
export async function generatePlan(withAi = checked("aiConsent")) {
  const button = $("generateBtn", HTMLButtonElement);
  if (!$("settingsForm", HTMLFormElement).reportValidity() || button.disabled) return;
  if (state.pendingCity) {
    showNotice(
      "Select a city from search results, or click a city shortcut, before building your plan.",
      true,
    );
    return;
  }
  const version = state.planVersion;
  setBusy(button, true, "Building your plan...");
  showNotice("");
  try {
    const body = JSON.stringify(requestBody({ ai_consent: withAi }));
    /** @type {PlanResponse} */
    const data = await getJson("/api/plan", { method: "POST", body });
    if (version === state.planVersion) showPlan(data);
  } catch (error) {
    if (version === state.planVersion) {
      showNotice(`Plan could not be generated: ${conciseError(error)} No advice was invented.`, true);
    }
  } finally {
    setBusy(button, false, "Build my protection plan");
  }
}

/** @param {string} question */
function questionProblem(question) {
  if (!checked("aiConsent")) {
    return "Enable Gemini personalization to ask a question. It sends the question and relevant context to Google.";
  }
  if (state.pendingCity) return "Select a city before asking a question.";
  if (question.length < MIN_QUESTION_LENGTH) return "Enter a question with at least five characters.";
  return null;
}

/** @param {SubmitEvent} event */
export async function askQuestion(event) {
  event.preventDefault();
  const question = $("question", HTMLTextAreaElement).value.trim();
  const problem = questionProblem(question);
  if (problem) {
    showNotice(problem, true);
    return;
  }
  const button = $("askBtn", HTMLButtonElement);
  const version = state.planVersion;
  button.disabled = true;
  button.textContent = "Generating a grounded answer...";
  $("askAnswer").replaceChildren(node("p", "Waiting for Gemini...", "muted"));
  try {
    /** @type {AskResponse} */
    const data = await getJson("/api/ask", {
      method: "POST",
      body: JSON.stringify(requestBody({ question })),
    });
    if (version === state.planVersion) renderAnswer(data.ai);
  } catch (error) {
    if (version === state.planVersion) {
      renderAnswerFallback(conciseError(error), Boolean(state.policy), () => void generatePlan(false));
    }
  } finally {
    button.disabled = false;
    button.textContent = "Ask with current air data ↗";
  }
}

export async function copyBrief() {
  if (!state.snapshot || !state.policy) {
    showNotice("Generate a plan before copying a community brief.", true);
    return;
  }
  try {
    await navigator.clipboard.writeText(communityBrief(state.snapshot, state.policy));
    showNotice("Community brief copied. It contains no household sensitivity selections.");
  } catch {
    showNotice("Clipboard was blocked by the browser; use Print plan instead.", true);
  }
}
