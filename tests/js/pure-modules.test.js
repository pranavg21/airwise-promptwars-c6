// Unit tests for browser modules that have no DOM side effects. Run with: npm test
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { communityBrief } from "../../static/js/brief.js";
import { placeLabel } from "../../static/js/city-search.js";
import { clock, safeNumber } from "../../static/js/dom.js";
import { currentHours, hasFiniteAqi, lowestHour } from "../../static/js/forecast.js";

const hour = (time, us_aqi) => ({ time: `2026-11-20T${time}`, us_aqi, pm2_5: 30 });

describe("safeNumber", () => {
  it("formats finite numbers and marks anything else as missing", () => {
    assert.equal(safeNumber(37.46, 1), "37.5");
    assert.equal(safeNumber(180), "180");
    for (const missing of [null, undefined, Number.NaN, Infinity, "12"])
      assert.equal(safeNumber(missing), "—");
  });
});

describe("clock", () => {
  it("shows month-day and local time from an ISO timestamp", () => {
    assert.equal(clock("2026-11-20T08:00"), "11-20 · 08:00");
    assert.equal(clock("2026-11-20"), "Unavailable");
    assert.equal(clock(null), "Unavailable");
  });
});

describe("currentHours", () => {
  it("starts at the model time and keeps at most 24 hours", () => {
    const hourly = Array.from({ length: 30 }, (_, i) => ({
      time: `2026-11-20T${String(i).padStart(2, "0")}:00`,
    }));
    const hours = currentHours({ model_time: "2026-11-20T03:00", hourly });
    assert.equal(hours.length, 24);
    assert.equal(hours[0].time, "2026-11-20T03:00");
  });

  it("returns nothing when the forecast is missing", () => {
    assert.deepEqual(currentHours(null), []);
    assert.deepEqual(currentHours({ model_time: "2026-11-20T03:00" }), []);
  });
});

describe("lowestHour", () => {
  it("picks the earliest hour with the lowest AQI and skips missing values", () => {
    const hours = [hour("08:00", 140), hour("09:00", null), hour("10:00", 103), hour("11:00", 103)];
    assert.equal(lowestHour(hours).time, "2026-11-20T10:00");
  });

  it("returns null when no hour has an AQI", () => {
    assert.equal(lowestHour([hour("08:00", null)]), null);
    assert.equal(lowestHour([]), null);
  });

  it("treats only finite numbers as chartable", () => {
    assert.equal(hasFiniteAqi(hour("08:00", 90)), true);
    assert.equal(hasFiniteAqi(hour("08:00", Number.NaN)), false);
    assert.equal(hasFiniteAqi(hour("08:00", null)), false);
  });
});

describe("placeLabel", () => {
  it("includes the region only when there is one", () => {
    assert.equal(placeLabel({ region: "Maharashtra", country: "India" }), "Maharashtra, India");
    assert.equal(placeLabel({ region: "", country: "India" }), "India");
  });
});

describe("communityBrief", () => {
  const snapshot = {
    location: { name: "Pune", country: "India" },
    source: "Open-Meteo / CAMS model forecast",
    model_time: "2026-11-20T08:00",
    timezone: "Asia/Kolkata",
    us_aqi: 137,
    pm2_5: 29.9,
    pm10: null,
  };

  it("names the place, source, time, scale and readings", () => {
    const brief = communityBrief(snapshot, { category: "Unhealthy for sensitive groups" });
    assert.match(brief, /Pune, India/);
    assert.match(brief, /modeled estimate as of 2026-11-20T08:00 \(Asia\/Kolkata\)/);
    assert.match(brief, /US EPA AQI: 137 · Unhealthy for sensitive groups\. Not India's official CPCB AQI/);
    assert.match(brief, /PM2\.5: 29\.9 µg\/m³ · PM10: — µg\/m³/);
  });

  it("never includes household health selections, even if present on the inputs", () => {
    const policy = { category: "Unhealthy", sensitive: true, cards: [{ id: "medical" }] };
    const brief = communityBrief({ ...snapshot, profile: { respiratory_sensitivity: true } }, policy);
    for (const privateWord of ["respiratory", "medical", "sensitive household", "children"]) {
      assert.doesNotMatch(brief.toLowerCase(), new RegExp(privateWord));
    }
  });
});
