/** Pure helpers over the hourly forecast returned by the API (no DOM access). */

const OUTLOOK_HOURS = 24;

/**
 * The next 24 forecast hours, starting at the model's current time.
 * @param {{model_time: string, hourly?: Array<{time: string}>}} snapshot
 */
export function currentHours(snapshot) {
  if (!snapshot || !Array.isArray(snapshot.hourly)) return [];
  return snapshot.hourly
    .filter((hour) => typeof hour.time === "string" && hour.time >= snapshot.model_time)
    .slice(0, OUTLOOK_HOURS);
}

/**
 * The first hour with the lowest modeled US AQI, or null when no hour has a value.
 * @param {Array<{time: string, us_aqi: number | null}>} hours
 */
export function lowestHour(hours) {
  let lowest = null;
  for (const hour of hours) {
    if (typeof hour.us_aqi === "number" && (lowest === null || hour.us_aqi < lowest.us_aqi)) lowest = hour;
  }
  return lowest;
}

/** @param {{us_aqi: unknown}} hour */
export function hasFiniteAqi(hour) {
  return typeof hour.us_aqi === "number" && Number.isFinite(hour.us_aqi);
}
