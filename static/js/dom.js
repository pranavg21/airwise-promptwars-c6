export const $ = id => document.getElementById(id);
export function node(tag, text = '', className = '') {
  const n = document.createElement(tag);
  n.textContent = String(text);
  if (className) n.className = className;
  return n;
}
export function safeNumber(v, decimals=0) {return typeof v === 'number' && Number.isFinite(v) ? v.toFixed(decimals) : '—';}
export function clock(s) {return typeof s === 'string' && s.length >= 16 ? `${s.slice(5,10)} · ${s.slice(11,16)}` : 'Unavailable';}
