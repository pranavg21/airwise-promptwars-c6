/** Building the plan, asking follow-up questions and sharing the community brief. */
import { communityBrief } from "./brief.js";
import { $, node } from "./dom.js";
import { conciseError, showNotice } from "./notice.js";
import { renderAi, renderAnswer, renderRecommendations } from "./plan-view.js";
import { displaySnapshot } from "./readings.js";
import { state } from "./state.js";
import { getJson } from "./transport.js";

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
  return state.aiReady ? "AVAILABLE · OPT IN" : "NOT CONFIGURED";
}

/** Clear the plan and invalidate any plan or answer still in flight. */
export function resetPlan() {
  state.planVersion++;
  state.policy = null;
  for (const [id, template] of initialPanels) {
    $(id).replaceChildren(...Array.from(template.childNodes, (child) => child.cloneNode(true)));
  }
  $("copyBtn").disabled = $("printBtn").disabled = true;
  $("aiStatus").textContent = aiStatusLabel();
}

function readProfile() {
  return {
    persona: $("persona").value,
    children: $("children").checked,
    older_adult: $("older").checked,
    respiratory_sensitivity: $("respiratory").checked,
    outdoor_minutes: Math.max(0, Math.min(MAX_OUTDOOR_MINUTES, Number($("outdoorMin").value) || 0)),
    start_hour: Number($("startHour").value),
    budget: $("budget").value,
    priorities: [...document.querySelectorAll(".priority:checked")].map((box) => box.value),
    language: $("language").value,
  };
}

function requestBody(extra = {}) {
  return { location: state.location, profile: readProfile(), ai_consent: $("aiConsent").checked, ...extra };
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.firstElementChild.textContent = label;
}

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

/** Request a plan for the current city and settings; late responses for old settings are dropped. */
export async function generatePlan() {
  const button = $("generateBtn");
  if (!$("settingsForm").reportValidity() || button.disabled) return;
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
    const data = await getJson("/api/plan", { method: "POST", body: JSON.stringify(requestBody()) });
    if (version === state.planVersion) showPlan(data);
  } catch (error) {
    if (version === state.planVersion) {
      showNotice(`Plan could not be generated: ${conciseError(error)} No advice was invented.`, true);
    }
  } finally {
    setBusy(button, false, "Build my protection plan");
  }
}

function questionProblem(question) {
  if (!$("aiConsent").checked) {
    return "Enable Gemini personalization to ask a question. It sends the question and relevant context to Google.";
  }
  if (state.pendingCity) return "Select a city before asking a question.";
  if (question.length < MIN_QUESTION_LENGTH) return "Enter a question with at least five characters.";
  return null;
}

/** @param {SubmitEvent} event */
export async function askQuestion(event) {
  event.preventDefault();
  const question = $("question").value.trim();
  const problem = questionProblem(question);
  if (problem) {
    showNotice(problem, true);
    return;
  }
  const button = $("askBtn");
  const version = state.planVersion;
  button.disabled = true;
  button.textContent = "Generating a grounded answer...";
  $("askAnswer").replaceChildren(node("p", "Waiting for Gemini...", "muted"));
  try {
    const data = await getJson("/api/ask", {
      method: "POST",
      body: JSON.stringify(requestBody({ question })),
    });
    if (version === state.planVersion) renderAnswer(data.ai);
  } catch (error) {
    if (version === state.planVersion) {
      $("askAnswer").replaceChildren(node("p", `Answer unavailable: ${conciseError(error)}`, "ask-answer"));
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
