/** The shareable community brief (pure: no DOM access, no household health choices). */
import { safeNumber } from "./dom.js";
/** @import { Policy, Snapshot } from "./types" */

/**
 * Plain-text brief for neighbours: place, source, time, readings and one community action.
 * Household sensitivity selections are deliberately not part of the input.
 * @param {Snapshot} snapshot Forecast snapshot from the API.
 * @param {Pick<Policy, "category">} policy Plan returned by the API.
 * @returns {string}
 */
export function communityBrief(snapshot, policy) {
  return [
    `AIRWISE · PUBLIC COMMUNITY AIR BRIEF · ${snapshot.location.name}, ${snapshot.location.country}`,
    `Source: ${snapshot.source}; modeled estimate as of ${snapshot.model_time} (${snapshot.timezone}).`,
    `US EPA AQI: ${safeNumber(snapshot.us_aqi)} · ${policy.category}. Not India's official CPCB AQI or a local station reading.`,
    `PM2.5: ${safeNumber(snapshot.pm2_5, 1)} µg/m³ · PM10: ${safeNumber(snapshot.pm10, 1)} µg/m³`,
    "Community action: avoid idling vehicles at shared entrances and check official local notices before scheduling outdoor events.",
    "Limits: modeled grid data do not establish local street, indoor, or personal exposure. Check official local notices.",
    "Data & credit: https://open-meteo.com/en/docs/air-quality-api (CAMS / Open-Meteo)",
  ].join("\n");
}
