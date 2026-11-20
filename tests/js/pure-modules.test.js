// Unit tests for browser modules that have no DOM side effects. Run with: npm test
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { communityBrief } from "../../static/js/brief.js";
import { cityQueryPath, placeLabel } from "../../static/js/city-search.js";
import { clock, safeNumber } from "../../static/js/dom.js";
import { hasFiniteAqi } from "../../static/js/chart.js";
import { isApiPath } from "../../static/js/transport.js";

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

describe("hasFiniteAqi", () => {
  it("treats only finite numbers as chartable", () => {
    assert.equal(hasFiniteAqi(hour("08:00", 90)), true);
    assert.equal(hasFiniteAqi(hour("08:00", Number.NaN)), false);
    assert.equal(hasFiniteAqi(hour("08:00", null)), false);
  });
});

describe("city search requests", () => {
  it("produces a valid API path for real city names, including apostrophes", () => {
    for (const name of ["Pune", "São Paulo", "St. John's", "L'Aquila", "Xi'an", "Saint-Étienne (Loire)"]) {
      const path = cityQueryPath(name);
      assert.ok(isApiPath(path), `${name} -> ${path}`);
      assert.equal(new URL(path, "http://local").searchParams.get("q"), name);
    }
  });

  it("still rejects paths outside the API", () => {
    assert.equal(isApiPath("https://example.com/api/geo"), false);
    assert.equal(isApiPath("/api/geo?q=<script>"), false);
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
