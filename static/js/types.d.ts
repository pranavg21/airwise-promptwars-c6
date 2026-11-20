/** Shapes of the AirWise API responses, mirroring the Pydantic models in airwise/models.py. */

export interface Hour {
  time: string;
  us_aqi: number | null;
  pm2_5: number | null;
  pm10: number | null;
}

/** An hour with a plottable AQI value. */
export type RatedHour = Hour & { us_aqi: number };

export interface Place {
  name: string;
  country: string;
  region: string;
  latitude: number;
  longitude: number;
}

export interface Snapshot {
  location: Place;
  retrieved_at: string;
  model_time: string;
  timezone: string;
  us_aqi: number | null;
  pm2_5: number | null;
  pm10: number | null;
  ozone: number | null;
  nitrogen_dioxide: number | null;
  hourly: Hour[];
  source: string;
  scale: string;
  data_kind: string;
  category: string;
  category_key: string;
  outlook: Hour[];
  outlook_lowest: Hour | null;
}

export interface Advice {
  id: string;
  title: string;
  detail: string;
  why: string;
  priority: "now" | "today" | "routine";
  reference: string;
}

export interface Shift {
  current_time: string;
  recommended_time: string;
  original_pm25: number;
  alternate_pm25: number;
  duration_min: number;
  relative_difference_pct: number;
  caution: string;
}

export interface Policy {
  category: string;
  concern: "low" | "moderate" | "high" | "very_high" | "unknown";
  headline: string;
  sensitive: boolean;
  cards: Advice[];
  swaps: Advice[];
  best_window: Hour | null;
  lowest_aqi: number | null;
  shift: Shift | null;
  trace: string[];
  disclaimer: string;
}

export interface AiReply {
  summary: string;
  steps: string[];
  rationale: string;
}

export interface PlanResponse {
  snapshot: Snapshot;
  policy: Policy;
  ai: AiReply | null;
  ai_status: "generated" | "not_requested" | "unavailable";
  ai_configured: boolean;
}

export interface AskResponse {
  ai: AiReply;
  ai_status: "generated";
  as_of: string;
  source: string;
  scale: string;
}
