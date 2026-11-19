/** Accessible vector chart with no dependencies or HTML injection. */
const NS = 'http://www.w3.org/2000/svg';
function svgNode(tag, attrs={}) {const n = document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));return n;}
function textSvg(x,y,text,anchor='start'){const n=svgNode('text',{x,y,fill:'#8a9989','font-size':11,'text-anchor':anchor,'font-family':'Arial, sans-serif'});n.textContent=text;return n;}
export function currentHours(snapshot) {
  if (!snapshot || !Array.isArray(snapshot.hourly)) return [];
  const from = snapshot.model_time;
  return snapshot.hourly.filter(h=>typeof h.time==='string' && h.time>=from).slice(0,24);
}
export function renderHourTable(target, hours) {
  target.replaceChildren();
  for (const h of hours) {
    const tr=document.createElement('tr');
    for (const t of [h.time.slice(5,16).replace('T',' · '), typeof h.us_aqi==='number'?h.us_aqi.toFixed(0):'—',typeof h.pm2_5==='number'?h.pm2_5.toFixed(1)+' µg/m³':'—']) {
      const td=document.createElement('td');td.textContent=t;tr.append(td);
    } target.append(tr);
  }
}
export function renderChart(target, hours) {
  target.replaceChildren();
  const valid=hours.filter(h=>typeof h.us_aqi==='number' && Number.isFinite(h.us_aqi));
  if(valid.length<2){const p=document.createElement('p');p.textContent='Too few valid forecast hours to draw a chart.';p.className='placeholder';target.append(p);return;}
  const w=600,h=200,left=40,right=20,top=14,bottom=32;
  const vals=valid.map(p=>p.us_aqi);
  const ymax=Math.max(50,Math.ceil(Math.max(...vals)*1.14/25)*25),ymin=0;
  const x=i=>left+i*(w-left-right)/Math.max(1,hours.length-1);
  const y=v=>top+(ymax-v)*(h-top-bottom)/(ymax-ymin);
  const svg=svgNode('svg',{viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':'Modeled hourly US AQI. Inspect hourly forecast data below for numeric values.'});
  svg.append(svgNode('title'));svg.firstChild.textContent='US AQI: next 24 hours';
  for(let i=0;i<=3;i++){const v=Math.round(ymax*i/3);svg.append(svgNode('line',{x1:left,y1:y(v),x2:w-right,y2:y(v),stroke:'#e4e9e2','stroke-dasharray':'4 5'}),textSvg(left-9,y(v)+4,String(v),'end'));}
  for(let i=0;i<hours.length;i+=Math.max(1,Math.floor(hours.length/5))){svg.append(textSvg(x(i),h-8,hours[i].time.slice(11,16),'middle'));}
  let path=''; let first=true;
  hours.forEach((pt,i)=>{
    if(typeof pt.us_aqi!=='number'||!Number.isFinite(pt.us_aqi)){first=true;return;}
    path+=`${first?'M':'L'} ${x(i).toFixed(1)} ${y(pt.us_aqi).toFixed(1)} `;first=false;
  });
  svg.append(svgNode('path',{d:path,stroke:'#6eaa3a','stroke-width':3.1,fill:'none','stroke-linejoin':'round','stroke-linecap':'round'}));
  for(let i=0;i<hours.length;i++)if(typeof hours[i].us_aqi==='number' && (i%3===0||i===hours.length-1))svg.append(svgNode('circle',{cx:x(i),cy:y(hours[i].us_aqi),r:3.3,fill:'#75b644',stroke:'#fff','stroke-width':2}));
  target.append(svg);
}
