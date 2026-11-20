/** Rendering of the rule-based plan, timing comparison, swaps and Gemini text. */
import { $, clock, node, safeNumber } from "./dom.js";
/** @import { Advice, AiReply, Hour, PlanResponse, Policy, Shift } from "./types" */

// Only these source links are rendered as anchors, whatever the server sends.
const WELL_KNOWN_REFERENCES = new Set([
  "https://www.who.int/news-room/questions-and-answers/item/air-pollution/personal-interventions-and-risk-communication",
  "https://www.who.int/news-room/questions-and-answers/item/air-pollution-personal-interventions-and-risk-communication",
  "https://www.epa.gov/wildfire-smoke-course/strategies-reduce-exposure-indoors",
  "https://open-meteo.com/en/docs/air-quality-api",
  "https://www.epa.gov/transportation-air-pollution-and-climate-change/what-you-can-do-reduce-pollution-vehicles-and",
  "https://www.epa.gov/schools/idle-free-schools-toolkit-healthy-school-environment",
  "https://www.epa.gov/indoor-air-quality-iaq/sources-indoor-particulate-matter-pm",
]);
/** @type {Record<string, string>} */
const AI_STATUS_LABELS = { generated: "✦ GEMINI GENERATED", not_requested: "NOT REQUESTED" };

/**
 * @param {Advice} card
 * @param {number} index
 */
function adviceCard(card, index) {
  const article = node("article", "", "advice-card");
  const top = node("div", "", "advice-top");
  top.append(
    node("span", String(index + 1).padStart(2, "0"), "advice-num"),
    node("span", card.priority.toUpperCase(), "advice-priority"),
  );
  const details = node("details");
  details.append(node("summary", "Why this matters"), node("p", card.why));
  if (WELL_KNOWN_REFERENCES.has(card.reference)) {
    const link = node("a", "Read the source ↗");
    link.href = card.reference;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    details.append(link);
  }
  article.append(top, node("h3", card.title), node("p", card.detail), details);
  return article;
}

/** @param {Advice} swap */
function swapCard(swap) {
  const card = node("article", "", "swap-card");
  card.append(
    node("div", "SUSTAINABLE ALTERNATIVE", "swap-label"),
    node("h3", swap.title),
    node("p", swap.detail),
    node("p", `Direct impact: ${swap.why}`, "swap-impact"),
  );
  return card;
}

/** @param {Shift} shift */
function shiftComparison(shift) {
  const timeline = node("div", "", "shift-timeline");
  timeline.append(
    node("span", clock(shift.current_time)),
    node("strong", "→"),
    node("span", clock(shift.recommended_time)),
  );
  return [
    node("div", `${safeNumber(shift.relative_difference_pct, 1)}%`, "shift-val"),
    node(
      "p",
      "Lower average modeled PM₂.₅ across the full activity. The alternative has an equal or lower peak modeled US AQI.",
      "shift-meta",
    ),
    timeline,
    node(
      "p",
      `${safeNumber(shift.original_pm25, 1)} → ${safeNumber(shift.alternate_pm25, 1)} µg/m³ · ${shift.duration_min}-minute planned activity`,
      "shift-meta",
    ),
  ];
}

/** @param {Hour} best */
function lowestHourOnly(best) {
  return [
    node("div", clock(best.time), "shift-val compact"),
    node(
      "p",
      `Lowest available modeled US AQI: ${safeNumber(best.us_aqi)}. No complete alternative met the timing comparison criteria.`,
      "shift-meta",
    ),
  ];
}

/** @param {Policy} policy Plan returned by /api/plan. */
function renderShift(policy) {
  const target = $("shiftResult");
  if (policy.shift) target.replaceChildren(...shiftComparison(policy.shift));
  else if (policy.best_window) target.replaceChildren(...lowestHourOnly(policy.best_window));
  else
    target.replaceChildren(
      node("p", "Hourly data are missing. No timing comparison is possible.", "placeholder"),
    );
  if (policy.concern === "very_high") {
    target.append(
      node(
        "p",
        "All outdoor time may require extra precautions. A lower AQI hour is not automatically safe.",
        "shift-meta",
      ),
    );
  }
}

/**
 * Render the deterministic plan: action cards, timing comparison, swaps and decision trace.
 * @param {Policy} policy Plan returned by /api/plan.
 */
export function renderRecommendations(policy) {
  $("copyBtn", HTMLButtonElement).disabled = $("printBtn", HTMLButtonElement).disabled = false;
  $("planSubtitle").textContent = policy.headline;
  $("recommendations").replaceChildren(...policy.cards.map(adviceCard));
  renderShift(policy);
  $("swaps").replaceChildren(...(policy.swaps || []).map(swapCard));
  $("traceList").replaceChildren(
    ...policy.trace.map((reason) => node("li", reason)),
    node("li", policy.disclaimer),
  );
}

/**
 * Render the Gemini briefing, or say plainly why there is none.
 * @param {Pick<PlanResponse, "ai_status" | "ai">} data
 */
export function renderAi(data) {
  const target = $("aiContent");
  $("aiStatus").textContent = AI_STATUS_LABELS[data.ai_status] ?? "UNAVAILABLE";
  if (data.ai_status === "not_requested") {
    target.replaceChildren(
      node(
        "p",
        "AI was not requested. Your independently verified rule-based plan is ready. Turn on Gemini personalization in the sidebar if you want an AI briefing.",
        "muted",
      ),
    );
    return;
  }
  if (data.ai_status !== "generated" || !data.ai) {
    target.replaceChildren(
      node(
        "p",
        "Gemini could not generate a briefing right now; it may have reached its daily limit. All deterministic, source-backed action cards remain usable.",
        "muted",
      ),
    );
    return;
  }
  const steps = node("ul");
  steps.append(...data.ai.steps.map((step) => node("li", step)));
  target.replaceChildren(
    node("p", data.ai.summary),
    node("h4", "Personalized next steps"),
    steps,
    node("p", data.ai.rationale),
  );
}

/**
 * Render a Gemini answer to a follow-up question.
 * @param {AiReply} reply
 */
export function renderAnswer(reply) {
  const box = node("div", "", "ask-answer");
  const steps = node("ul");
  steps.append(...reply.steps.map((step) => node("li", step)));
  box.append(
    node("strong", "✦ Gemini answer — based on current air model data"),
    node("p", reply.summary),
    steps,
    node("p", reply.rationale),
  );
  $("askAnswer").replaceChildren(box);
}

/**
 * When Gemini cannot answer, point to guidance that does not depend on it.
 * @param {string} reason Why the answer failed, already shortened for display.
 * @param {boolean} hasPlan Whether a rule-based plan for the current settings is on screen.
 * @param {() => void} buildPlan Builds the rule-based plan without Gemini.
 */
export function renderAnswerFallback(reason, hasPlan, buildPlan) {
  const box = node("div", "", "ask-answer");
  box.append(node("strong", `Answer unavailable: ${reason}`));
  const action = node("button", hasPlan ? "Go to my rule-based plan" : "Build plan without Gemini");
  action.type = "button";
  action.addEventListener("click", hasPlan ? () => $("recommendations").focus() : buildPlan);
  const next = hasPlan
    ? "Your rule-based plan does not depend on Gemini: its action cards and timing comparison still apply."
    : "You can still build a rule-based plan from the same air data. It does not use Gemini.";
  box.append(node("p", next), action);
  $("askAnswer").replaceChildren(box);
}
