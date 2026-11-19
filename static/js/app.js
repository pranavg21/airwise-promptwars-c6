/** AirWise browser UI: no frameworks, no third-party scripts, no inserted untrusted HTML. */
import {$, node, safeNumber, clock} from './dom.js';
import {renderRecommendations, renderAi} from './plan-view.js';
import {getJson} from './transport.js';
import {renderChart, renderHourTable, currentHours} from './chart.js';

const EXAMPLES = Object.freeze({
  delhi: {name: 'New Delhi', country: 'India', region: 'Delhi', latitude: 28.6139, longitude: 77.2090},
  mumbai: {name: 'Mumbai', country: 'India', region: 'Maharashtra', latitude: 19.0760, longitude: 72.8777},
  pune: {name: 'Pune', country: 'India', region: 'Maharashtra', latitude: 18.5204, longitude: 73.8567},
  bengaluru: {name: 'Bengaluru', country: 'India', region: 'Karnataka', latitude: 12.9716, longitude: 77.5946},
});

const state = {location: EXAMPLES.delhi, snapshot: null, policy: null, pendingCity: false, aiReady: false};
function conciseError(err) {return err instanceof Error ? err.message : 'Something went wrong. Please retry.';}
function showNotice(message, error=false) {
  const alert = $('notice'); alert.textContent = message; alert.hidden = !message;
  alert.style.background = error ? '#fff1e2' : '#eff7e6';
  alert.style.borderColor = error ? '#e5be94' : '#d9e9cb';
}
// Invalidate asynchronous work when the inputs it describes change.
let contextVersion = 0;
let airVersion = 0;
let searchSequence = 0;
const planPanels = ['planSubtitle', 'recommendations', 'swaps', 'shiftResult', 'traceList', 'aiContent', 'askAnswer'];
const initialPanels = new Map(planPanels.map(id => [id, $(id).cloneNode(true)]));

function resetPlan() {
  contextVersion++;
  state.policy = null;
  for (const [id, template] of initialPanels) {
    $(id).replaceChildren(...Array.from(template.childNodes, n => n.cloneNode(true)));
  }
  $('copyBtn').disabled = $('printBtn').disabled = true;
  $('aiStatus').textContent = state.aiReady ? 'AVAILABLE · OPT IN' : 'NOT CONFIGURED';
}

function resetReadings() {
  airVersion++;
  state.snapshot = null;
  for (const id of ['aqiValue', 'pm25', 'pm10', 'bestAQI', 'aqiTime', 'bestTime']) $(id).textContent = '—';
  $('feedStatus').textContent = 'AWAITING DATA';
  $('aqiCategory').textContent = 'Awaiting forecast';
  $('dataStamp').textContent = 'No forecast loaded';
  $('chart').replaceChildren();
  $('hourlyTable').replaceChildren();
  resetPlan();
}

function setLocation(location) {
  searchSequence++;
  state.location = location;
  state.pendingCity = false; $('citySearch').value = location.name;
  $('chosenCity').textContent = `${location.name}, ${location.region ? location.region + ', ' : ''}${location.country}`;
  $('cityResults').hidden = true; $('citySearch').setAttribute('aria-expanded', 'false');
  $('aqiCity').textContent = location.name.toUpperCase();
  showNotice('');
  void loadSnapshot();
}
function profile() {
  return {
    persona: $('persona').value, children: $('children').checked, older_adult: $('older').checked,
    respiratory_sensitivity: $('respiratory').checked,
    outdoor_minutes: Math.max(0,Math.min(480,Number($('outdoorMin').value)||0)),
    start_hour: Number($('startHour').value), budget: $('budget').value,
    priorities: [...document.querySelectorAll('.priority:checked')].map(x => x.value),
    language: $('language').value,
  };
}
function requestBody() {return {location: state.location, profile: profile(), ai_consent: $('aiConsent').checked};}
async function healthCheck() {
  try {
    const data = await getJson('/api/health'); state.aiReady = data.ai_configured === true;
    $('aiStatus').textContent = state.aiReady ? 'AVAILABLE · OPT IN' : 'NOT CONFIGURED';
  } catch {state.aiReady = false; $('aiStatus').textContent = 'UNAVAILABLE';}
}
function displaySnapshot(s) {
  state.snapshot = s;
  $('aqiValue').textContent = safeNumber(s.us_aqi);
  $('feedStatus').textContent = 'LATEST MODEL ESTIMATE';
  const {category, severity} = classifyAqi(s.us_aqi);
  $('aqiCategory').textContent = category;
  $('aqiCategory').style.color = severity === 0 ? '#a9efb9' : severity === 1 ? '#e9e183' : severity === 2 ? '#ffc48e' : '#ffc2ba';
  $('aqiTime').textContent = `${clock(s.model_time)} · ${s.timezone} local`;
  $('pm25').textContent = safeNumber(s.pm2_5, 1);
  $('pm10').textContent = safeNumber(s.pm10, 1);
  $('aqiCity').textContent = s.location.name.toUpperCase();
  $('dataStamp').textContent = `Open-Meteo/CAMS model · ${clock(s.model_time)} (${s.timezone}); fetched ${new Date(s.retrieved_at).toLocaleString()}`;
  const hours = currentHours(s);
  const usable = hours.filter(h => typeof h.us_aqi === 'number');
  if (usable.length) {
    const min = usable.reduce((a,b)=>a.us_aqi <= b.us_aqi ? a:b);
    $('bestAQI').textContent = safeNumber(min.us_aqi);
    $('bestTime').textContent = `${clock(min.time)} local · not necessarily safe`;
  } else {$('bestAQI').textContent = '—'; $('bestTime').textContent = 'No valid 24-hour forecast';}
  renderChart($('chart'), hours);
  renderHourTable($('hourlyTable'), hours);
}
function classifyAqi(v) {
  if (typeof v !== 'number') return {category:'AQI unavailable',severity:3};
  if (v<=50)return {category:'Good',severity:0};
  if (v<=100)return {category:'Moderate',severity:1};
  if (v<=150)return {category:'Unhealthy for sensitive groups',severity:2};
  if (v<=200)return {category:'Unhealthy',severity:3};
  if (v<=300)return {category:'Very unhealthy',severity:3};
  return {category:'Hazardous',severity:3};
}
async function loadSnapshot() {
  if (state.pendingCity) return;
  resetReadings();
  const version = airVersion;
  $('aqiValue').textContent = '···'; $('aqiCategory').textContent = 'Connecting to air model...';
  try {
    const s = await getJson('/api/air', {method:'POST', body: JSON.stringify(state.location)});
    if (version !== airVersion) return;
    displaySnapshot(s);
  } catch(err) {
    if (version !== airVersion) return;
    if (state.location) { $('aqiValue').textContent = '—'; $('aqiCategory').textContent='Forecast unavailable'; }
    $('feedStatus').textContent = 'DATA UNAVAILABLE';
    showNotice(`Live data could not be retrieved: ${conciseError(err)} No readings have been fabricated.`,true);
  }
}
async function generatePlan() {
  if (!$('settingsForm').reportValidity()) return;
  if(state.pendingCity){showNotice('Select a city from search results, or click a city shortcut, before building your plan.',true);return;}
  const button=$('generateBtn');
  if (button.disabled) return;
  const version = contextVersion;
  button.disabled=true;button.firstElementChild.textContent='Building your plan...';
  showNotice('');
  try {
    const data = await getJson('/api/plan',{method:'POST',body:JSON.stringify(requestBody())});
    if (version !== contextVersion) return;
    airVersion++;
    displaySnapshot(data.snapshot);state.policy = data.policy;renderRecommendations(data.policy);renderAi(data);
    showNotice(`Plan refreshed from modeled air data. ${data.ai_status === 'generated' ? 'Gemini personalization generated.' : 'Source-backed recommendations ready.'}`);
    $('recommendations').focus({preventScroll:true});
    $('recommendations').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  } catch(err){if(version === contextVersion) showNotice(`Plan could not be generated: ${conciseError(err)} No advice was invented.`,true);}
  finally{button.disabled=false;button.firstElementChild.textContent='Build my protection plan';}
}

async function searchCity() {
  const q=$('citySearch').value.trim();const dropdown=$('cityResults');
  if(q.length<3){dropdown.hidden=true;showNotice('Type at least 3 characters to search a city.',true);return;}
  const sequence=++searchSequence;dropdown.hidden=false;dropdown.replaceChildren(node('p','Searching cities...','field-help'));
  try {
    const payload=await getJson(`/api/geo?q=${encodeURIComponent(q)}`);
    if(sequence!==searchSequence)return;
    dropdown.replaceChildren();
    if(!payload.results.length){dropdown.append(node('p','No matching city found. Try a longer name.','field-help'));return;}
    payload.results.forEach(city=>{
      const button=node('button',city.name);button.type='button';button.setAttribute('role','option');button.setAttribute('aria-selected','false');
      button.append(node('small',`${city.region ? city.region+', ':''}${city.country}`));
      button.addEventListener('click',()=>setLocation(city));dropdown.append(button);
    }); $('citySearch').setAttribute('aria-expanded','true');
  } catch(err){if(sequence===searchSequence)dropdown.replaceChildren(node('p',conciseError(err),'field-help'));}
}
function createCommunityBrief() {
  if(!state.snapshot || !state.policy)return null;
  const s=state.snapshot,p=state.policy;
  return [
    `AIRWISE · PUBLIC COMMUNITY AIR BRIEF · ${s.location.name}, ${s.location.country}`,
    `Source: ${s.source}; modeled estimate as of ${s.model_time} (${s.timezone}).`,
    `US EPA AQI: ${safeNumber(s.us_aqi)} · ${p.category}. Not India's official CPCB AQI or a local station reading.`,
    `PM2.5: ${safeNumber(s.pm2_5,1)} µg/m³ · PM10: ${safeNumber(s.pm10,1)} µg/m³`,
    'Community action: avoid idling vehicles at shared entrances and check official local notices before scheduling outdoor events.',
    `Limits: modeled grid data do not establish local street, indoor, or personal exposure. Check official local notices.`,
    'Data & credit: https://open-meteo.com/en/docs/air-quality-api (CAMS / Open-Meteo)',
  ].join('\n');
}
async function copyBrief() {
  const summary=createCommunityBrief();if(!summary){showNotice('Generate a plan before copying a community brief.',true);return;}
  try {await navigator.clipboard.writeText(summary);showNotice('Community brief copied. It contains no household sensitivity selections.');}
  catch {showNotice('Clipboard was blocked by the browser; use Print plan instead.',true);}
}
async function askQuestion(e) {
  e.preventDefault();if(!$('aiConsent').checked){showNotice('Enable Gemini personalization to ask a question. It sends the question and relevant context to Google.',true);return;}
  if(state.pendingCity){showNotice('Select a city before asking a question.',true);return;}
  const question=$('question').value.trim();
  if(question.length<5){showNotice('Enter a question with at least five characters.',true);return;}
  const button=$('askBtn');button.disabled=true;button.textContent='Generating a grounded answer...';
  const version = contextVersion;
  const answer=$('askAnswer');answer.replaceChildren(node('p','Waiting for Gemini...','muted'));
  try {
    const body={...requestBody(),question};
    const data=await getJson('/api/ask',{method:'POST',body:JSON.stringify(body)});
    if (version !== contextVersion) return;
    const r=data.ai;answer.replaceChildren();const box=node('div','','ask-answer');
    box.append(node('strong','✦ Gemini answer — based on current air model data'),node('p',r.summary));
    const list=node('ul');r.steps.forEach(step=>list.append(node('li',step)));box.append(list,node('p',r.rationale));answer.append(box);
  } catch(err){if(version === contextVersion) answer.replaceChildren(node('p',`Answer unavailable: ${conciseError(err)}`,'ask-answer'));}
  finally{button.disabled=false;button.textContent='Ask with current air data ↗';}
}
function bindEvents() {
  $('settingsForm').addEventListener('submit',e=>{e.preventDefault();void generatePlan();});
  $('settingsForm').addEventListener('change',e=>{if(e.target.id !== 'citySearch'){resetPlan();showNotice('Preferences changed. Build a plan for the new settings.');}});
  $('recommendations').addEventListener('click',e=>{if(e.target.closest('#emptyGenerate')) void generatePlan();});
  $('citySearchBtn').addEventListener('click',()=>void searchCity());
  $('citySearch').addEventListener('input',()=>{state.pendingCity=true;searchSequence++;resetReadings();$('aqiCity').textContent='SELECT CITY';$('chosenCity').textContent='Select a search result or city shortcut';$('cityResults').hidden=true;$('citySearch').setAttribute('aria-expanded','false');});
  $('citySearch').addEventListener('keydown',e=>{
    if(e.key==='Enter'){e.preventDefault();void searchCity();}
    if(e.key==='ArrowDown' && !$('cityResults').hidden){e.preventDefault();$('cityResults').querySelector('button')?.focus();}
    if(e.key==='Escape'){$('cityResults').hidden=true;$('citySearch').setAttribute('aria-expanded','false');}
  });
  $('cityResults').addEventListener('keydown',e=>{
    const buttons=[...$('cityResults').querySelectorAll('button')];const pos=buttons.indexOf(document.activeElement);
    if(e.key==='ArrowDown'){e.preventDefault();buttons[Math.min(pos+1,buttons.length-1)]?.focus();}
    if(e.key==='ArrowUp'){e.preventDefault();if(pos===0)$('citySearch').focus();else buttons[Math.max(0,pos-1)]?.focus();}
    if(e.key==='Escape'){$('cityResults').hidden=true;$('citySearch').focus();}
  });
  document.querySelectorAll('[data-city]').forEach(b=>b.addEventListener('click',()=>setLocation(EXAMPLES[b.dataset.city])));
  document.addEventListener('click',e=>{if(!e.target.closest('.search-wrap')&&!e.target.closest('.city-results')){$('cityResults').hidden=true;$('citySearch').setAttribute('aria-expanded','false');}});
  $('aboutBtn').addEventListener('click',()=>{$('methodology').scrollIntoView({behavior:'smooth'});});
  $('refreshBtn').addEventListener('click',()=>void loadSnapshot());
  $('copyBtn').addEventListener('click',()=>void copyBrief());
  $('printBtn').addEventListener('click',()=>window.print());
  $('askForm').addEventListener('submit',e=>void askQuestion(e));
  document.querySelectorAll('.sample-question').forEach(b=>b.addEventListener('click',()=>{$('question').value=b.textContent.trim();$('question').focus();}));
}
bindEvents();
setLocation(EXAMPLES.delhi);
void healthCheck();
