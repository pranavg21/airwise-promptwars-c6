/** Accessible SVG chart and data table for the 24-hour outlook; no dependencies, no HTML injection. */
import { hasFiniteAqi } from "./forecast.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 600;
const HEIGHT = 200;
const MARGIN = { left: 40, right: 20, top: 14, bottom: 32 };
const Y_HEADROOM = 1.14;
const Y_STEP = 25;
const MIN_Y_MAX = 50;
const GRID_LINES = 3;
const TIME_LABELS = 5;
const POINT_EVERY_HOURS = 3;
const LINE_COLOR = "#6eaa3a";
const POINT_COLOR = "#75b644";
const GRID_COLOR = "#e4e9e2";

function svgNode(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}

function label(x, y, text, anchor = "start") {
  const element = svgNode("text", {
    x,
    y,
    class: "chart-label",
    "font-size": 11,
    "text-anchor": anchor,
    "font-family": "Arial, sans-serif",
  });
  element.textContent = text;
  return element;
}

/** Map an hour index and an AQI value to SVG coordinates. */
function scales(hours, valid) {
  const yMax = Math.max(
    MIN_Y_MAX,
    Math.ceil((Math.max(...valid.map((h) => h.us_aqi)) * Y_HEADROOM) / Y_STEP) * Y_STEP,
  );
  const plotWidth = WIDTH - MARGIN.left - MARGIN.right;
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  return {
    yMax,
    x: (index) => MARGIN.left + (index * plotWidth) / Math.max(1, hours.length - 1),
    y: (value) => MARGIN.top + ((yMax - value) * plotHeight) / yMax,
  };
}

function gridLines(scale) {
  const elements = [];
  for (let step = 0; step <= GRID_LINES; step++) {
    const value = Math.round((scale.yMax * step) / GRID_LINES);
    const y = scale.y(value);
    elements.push(
      svgNode("line", {
        x1: MARGIN.left,
        y1: y,
        x2: WIDTH - MARGIN.right,
        y2: y,
        stroke: GRID_COLOR,
        "stroke-dasharray": "4 5",
      }),
      label(MARGIN.left - 9, y + 4, String(value), "end"),
    );
  }
  return elements;
}

function timeLabels(hours, scale) {
  const elements = [];
  const every = Math.max(1, Math.floor(hours.length / TIME_LABELS));
  for (let index = 0; index < hours.length; index += every) {
    elements.push(label(scale.x(index), HEIGHT - 8, hours[index].time.slice(11, 16), "middle"));
  }
  return elements;
}

/** One path; gaps in the forecast start a new segment instead of drawing through them. */
function trendLine(hours, scale) {
  let path = "";
  let startSegment = true;
  hours.forEach((hour, index) => {
    if (!hasFiniteAqi(hour)) {
      startSegment = true;
      return;
    }
    path += `${startSegment ? "M" : "L"} ${scale.x(index).toFixed(1)} ${scale.y(hour.us_aqi).toFixed(1)} `;
    startSegment = false;
  });
  return svgNode("path", {
    d: path,
    stroke: LINE_COLOR,
    "stroke-width": 3.1,
    fill: "none",
    "stroke-linejoin": "round",
    "stroke-linecap": "round",
  });
}

function points(hours, scale) {
  const isMarked = (index) => index % POINT_EVERY_HOURS === 0 || index === hours.length - 1;
  return hours
    .map((hour, index) => ({ hour, index }))
    .filter(({ hour, index }) => typeof hour.us_aqi === "number" && isMarked(index))
    .map(({ hour, index }) =>
      svgNode("circle", {
        cx: scale.x(index),
        cy: scale.y(hour.us_aqi),
        r: 3.3,
        fill: POINT_COLOR,
        stroke: "#fff",
        "stroke-width": 2,
      }),
    );
}

/**
 * Draw the modeled US AQI line for the given hours into `target`.
 * @param {HTMLElement} target
 * @param {Array<{time: string, us_aqi: number | null}>} hours
 */
export function renderChart(target, hours) {
  target.replaceChildren();
  const valid = hours.filter(hasFiniteAqi);
  if (valid.length < 2) {
    const placeholder = document.createElement("p");
    placeholder.textContent = "Too few valid forecast hours to draw a chart.";
    placeholder.className = "placeholder";
    target.append(placeholder);
    return;
  }
  const scale = scales(hours, valid);
  const svg = svgNode("svg", {
    viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
    role: "img",
    "aria-label": "Modeled hourly US AQI. Inspect hourly forecast data below for numeric values.",
  });
  const title = svgNode("title");
  title.textContent = "US AQI: next 24 hours";
  svg.append(
    title,
    ...gridLines(scale),
    ...timeLabels(hours, scale),
    trendLine(hours, scale),
    ...points(hours, scale),
  );
  target.append(svg);
}

/**
 * Fill the accessible table that carries the same hourly values as the chart.
 * @param {HTMLElement} target A tbody element.
 * @param {Array<{time: string, us_aqi: number | null, pm2_5: number | null}>} hours
 */
export function renderHourTable(target, hours) {
  target.replaceChildren();
  for (const hour of hours) {
    const row = document.createElement("tr");
    const cells = [
      hour.time.slice(5, 16).replace("T", " · "),
      typeof hour.us_aqi === "number" ? hour.us_aqi.toFixed(0) : "—",
      typeof hour.pm2_5 === "number" ? `${hour.pm2_5.toFixed(1)} µg/m³` : "—",
    ];
    for (const text of cells) {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.append(cell);
    }
    target.append(row);
  }
}
