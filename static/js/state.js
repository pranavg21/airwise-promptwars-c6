/** Shared page state. */
/** @import { Place, Policy, Snapshot } from "./types" */

/** @type {Readonly<Record<string, Place>>} */
export const EXAMPLE_CITIES = Object.freeze({
  delhi: { name: "New Delhi", country: "India", region: "Delhi", latitude: 28.6139, longitude: 77.209 },
  mumbai: { name: "Mumbai", country: "India", region: "Maharashtra", latitude: 19.076, longitude: 72.8777 },
  pune: { name: "Pune", country: "India", region: "Maharashtra", latitude: 18.5204, longitude: 73.8567 },
  bengaluru: {
    name: "Bengaluru",
    country: "India",
    region: "Karnataka",
    latitude: 12.9716,
    longitude: 77.5946,
  },
});

/**
 * The version counters let a late response see that the inputs it describes have changed,
 * so a slow answer for one city or profile is never shown under another.
 * @type {{
 *   location: Place, snapshot: Snapshot | null, policy: Policy | null, pendingCity: boolean,
 *   aiReady: boolean, planVersion: number, readingsVersion: number, searchVersion: number
 * }}
 */
export const state = {
  location: EXAMPLE_CITIES.delhi,
  snapshot: null,
  policy: null,
  pendingCity: false,
  aiReady: false,
  planVersion: 0,
  readingsVersion: 0,
  searchVersion: 0,
};
