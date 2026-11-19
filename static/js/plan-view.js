import {$, node, safeNumber, clock} from './dom.js';

const WELL_KNOWN_REFERENCES = new Set([
  'https://www.who.int/news-room/questions-and-answers/item/air-pollution/personal-interventions-and-risk-communication',
  'https://www.who.int/news-room/questions-and-answers/item/air-pollution-personal-interventions-and-risk-communication',
  'https://www.epa.gov/wildfire-smoke-course/strategies-reduce-exposure-indoors',
  'https://open-meteo.com/en/docs/air-quality-api',
  'https://www.epa.gov/transportation-air-pollution-and-climate-change/what-you-can-do-reduce-pollution-vehicles-and',
  'https://www.epa.gov/schools/idle-free-schools-toolkit-healthy-school-environment',
  'https://www.epa.gov/indoor-air-quality-iaq/sources-indoor-particulate-matter-pm',
]);
export function renderRecommendations(policy) {
  $('copyBtn').disabled = $('printBtn').disabled = false;
  $('planSubtitle').textContent = policy.headline;
  const target = $('recommendations'); target.replaceChildren();
  policy.cards.forEach((card, i) => {
    const article = node('article', '', 'advice-card');
    const top = node('div','','advice-top'); top.append(node('span', String(i+1).padStart(2,'0'),'advice-num'),node('span', card.priority.toUpperCase(),'advice-priority'));
    article.append(top,node('h3',card.title),node('p',card.detail));
    const details = node('details'); details.append(node('summary','Why this matters'),node('p',card.why));
    if (WELL_KNOWN_REFERENCES.has(card.reference)) {
      const a = node('a','Read the source ↗'); a.href = card.reference; a.target='_blank'; a.rel='noopener noreferrer'; details.append(a);
    }
    article.append(details); target.append(article);
  });
  renderShift(policy.shift, policy.best_window, policy.category);
  renderSwaps(policy.swaps);
  const trace = $('traceList'); trace.replaceChildren(...policy.trace.map(t=>node('li',t)));
  trace.append(node('li',policy.disclaimer));
}
function renderSwaps(swaps) {
  const target=$('swaps');target.replaceChildren();
  for(const swap of (swaps || [])) {
    const card=node('article','','swap-card');
    card.append(node('div','SUSTAINABLE ALTERNATIVE','swap-label'),node('h3',swap.title),node('p',swap.detail),node('p',`Direct impact: ${swap.why}`,'swap-impact'));
    target.append(card);
  }
}
function renderShift(shift,best,category) {
  const target=$('shiftResult');target.replaceChildren();
  if (shift) {
    target.append(node('div',`${safeNumber(shift.relative_difference_pct,1)}%`,'shift-val'));
    target.append(node('p','Lower average modeled PM₂.₅ across the full activity. The alternative has an equal or lower peak modeled US AQI.','shift-meta'));
    const t=node('div','','shift-timeline');t.append(node('span',clock(shift.current_time)),node('strong','→'),node('span',clock(shift.recommended_time)));
    target.append(t,node('p',`${safeNumber(shift.original_pm25,1)} → ${safeNumber(shift.alternate_pm25,1)} µg/m³ · ${shift.duration_min}-minute planned activity`,'shift-meta'));
  } else if(best) {
    target.append(node('div',clock(best.time),'shift-val')); target.querySelector('.shift-val').style.fontSize='28px';
    target.append(node('p',`Lowest available modeled US AQI: ${safeNumber(best.us_aqi)}. No complete alternative met the timing comparison criteria.`,`shift-meta`));
  } else target.append(node('p','Hourly data are missing. No timing comparison is possible.','placeholder'));
  if (category==='Hazardous' || category==='Very unhealthy') target.append(node('p','All outdoor time may require extra precautions. A lower AQI hour is not automatically safe.','shift-meta'));
}
export function renderAi(data) {
  const target = $('aiContent');target.replaceChildren();
  $('aiStatus').textContent = data.ai_status === 'generated' ? '✦ GEMINI GENERATED' : data.ai_status === 'not_requested' ? 'NOT REQUESTED' : 'UNAVAILABLE';
  if (data.ai_status !== 'generated' || !data.ai) {
    target.append(node('p', data.ai_status === 'not_requested' ? 'AI was not requested. Your independently verified rule-based plan is ready. Turn on Gemini personalization in the sidebar if you want an AI briefing.' : 'Gemini could not generate a valid response. All deterministic, source-backed action cards remain usable. Verify the server key and quota.','muted'));
    return;
  }
  target.append(node('p',data.ai.summary),node('h4','Personalized next steps'));
  const list=node('ul'); data.ai.steps.forEach(s=>list.append(node('li',s)));target.append(list,node('p',data.ai.rationale));
}
