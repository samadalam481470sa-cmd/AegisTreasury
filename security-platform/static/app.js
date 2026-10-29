/* No external scripts or hosted telemetry. Data remains within this installation. */
'use strict';
const state = { user: null, dashboard: {}, alerts: [], events: [], services: [], filter: 'all', active: 'overview' };
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const friendly = str => String(str || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const when = s => s ? new Date(s).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '—';
const shortTime = s => new Date(s).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
const badge = text => `<span class="badge ${esc(text)}">${esc(friendly(text))}</span>`;
function csrfToken() { const found = document.cookie.split('; ').find(item => item.startsWith('aegis_csrf=')); return found ? decodeURIComponent(found.split('=').slice(1).join('=')) : ''; }
async function api(path, options={}) {
  const headers = {'Accept':'application/json', ...(options.body ? {'Content-Type':'application/json'} : {})};
  if (options.method && options.method !== 'GET') headers['X-CSRF-Token'] = csrfToken();
  const res = await fetch(path, {credentials:'same-origin', ...options, headers:{...headers,...options.headers}});
  let payload; try { payload = await res.json(); } catch { payload = {}; }
  if (!res.ok) { const msg = typeof payload.detail === 'string' ? payload.detail : 'Request failed'; const error = new Error(msg); error.status = res.status; throw error; }
  return payload;
}
function showLogin() {$('app-shell').classList.add('hidden');$('login-screen').classList.remove('hidden');}
function showApp(user) {
  state.user=user;
  $('login-screen').classList.add('hidden');$('app-shell').classList.remove('hidden');
  $('user-email').textContent=user.email;$('user-role').textContent=user.role;$('user-avatar').textContent=user.email.slice(0,1).toUpperCase();
  const admin = user.role === 'admin'; const writer = admin || user.role === 'analyst';
  document.querySelectorAll('.admin-only').forEach(el => el.classList.toggle('hidden',!admin));
  document.querySelectorAll('.writer-only').forEach(el => el.classList.toggle('hidden',!writer));
}
function errorMessage(message) { $('error-banner').textContent=message;$('error-banner').classList.remove('hidden'); }
async function reload() {
  try {
    $('error-banner').classList.add('hidden');
    const [dashboard,alerts,events,services] = await Promise.all([
      api('/api/dashboard'), api('/api/alerts'),api('/api/events?limit=200'),api('/api/services')]);
    Object.assign(state,{dashboard,alerts,events,services});
    $('last-sync').textContent=shortTime(new Date());
    renderOverview();renderAlerts();renderEvents();renderServices();
    if(state.active==='audit'&&state.user.role==='admin') await renderAudit();
  } catch(e) { if(e.status===401) showLogin(); else errorMessage(e.message); }
}
function switchView(view) {
  if(view==='audit' && state.user?.role!=='admin') return;
  state.active=view;
  const names={overview:['Overview','SECURITY OVERVIEW','Intelligence Overview','Monitor security signals, financial risk and infrastructure health in one place.'], alerts:['Threat intelligence','DETECTION & RESPONSE','Threat Intelligence','Triage financial fraud, access threats and suspicious security activity.'],events:['Event explorer','EVENT PROCESSING','Event Explorer','Investigate event telemetry and inspect explainable detection signals.'],services:['Infrastructure','SERVICE RELIABILITY','Infrastructure Health','Operational observability across essential payment and identity services.'],audit:['Audit integrity','COMPLIANCE & TRUST','Audit Integrity','Verify the cryptographic continuity of privileged actions and risk events.']};
  const [crumb,eye,title,description]=names[view];
  $('breadcrumb-current').textContent=crumb;$('page-eyebrow').textContent=eye;$('page-title').textContent=title;$('page-description').textContent=description;
  document.querySelectorAll('.view').forEach(el=>el.classList.toggle('active',el.id===`view-${view}`));
  document.querySelectorAll('.nav-link').forEach(el=>el.classList.toggle('active',el.dataset.view===view));
  if(view==='audit') renderAudit();
}
const tdEmpty = (cols, msg) => `<tr><td class="no-data" colspan="${cols}">${esc(msg)}</td></tr>`;
function renderOverview() {
  const d=state.dashboard, open=(d.alerts?.open||0)+(d.alerts?.investigating||0);
  $('kpi-events').textContent=d.event_count??0;$('kpi-alerts').textContent=open;$('kpi-risk').innerHTML=`${esc(d.avg_risk??0)}<small>/100</small>`;
  $('kpi-services').textContent=`${d.active_services||0}/${d.total_services||0}`;$('alert-nav-count').textContent=open;
  const top=state.alerts.slice(0,5);
  $('overview-alerts').innerHTML=top.map(a=>`<tr><td><strong>${esc(a.title)}</strong><small>#${a.id} · ${esc(friendly(a.kind))}</small></td><td>${esc(a.actor)}</td><td>${badge(a.severity)}</td><td>${badge(a.status)}</td><td>${esc(when(a.created_at))}</td></tr>`).join('') || tdEmpty(5,'No threats detected yet. Seed demo events to populate this view.');
  const severities=['critical','high','medium','low'], colors=['#c05c70','#e3a062','#6383e4','#4cd0af'];
  const total=severities.reduce((acc,k)=>acc+(d.severity?.[k]||0),0);
  $('ring-total').textContent=total;
  $('severity-list').innerHTML=severities.map((k,i)=>`<div class="severity-row"><span class="sev-dot ${k}"></span><span>${friendly(k)}</span><b>${d.severity?.[k]||0}</b></div>`).join('');
  const ring=$('severity-ring');
  const stops=[];let count=0;
  severities.forEach((k,i)=>{const n=d.severity?.[k]||0;const span=total ? n/total*100 : 0;if(span){stops.push(`${colors[i]} ${count}% ${count+span}%`);count+=span;}});
  ring.setAttribute('aria-label',severities.map(k=>`${k}: ${d.severity?.[k]||0}`).join(', '));
  // Segment colors already appear in the legend; dynamic SVG replaces any hardcoded ring segments.
  ring.querySelectorAll('svg').forEach(node=>node.remove());
  const svg=createSvg('svg',{viewBox:'0 0 176 176',width:'176',height:'176','aria-hidden':'true'});
  svg.appendChild(createSvg('circle',{cx:88,cy:88,r:74,fill:'none',stroke:'#23394b','stroke-width':23}));
  let offset=0;severities.forEach((k,i)=>{const portion=total ? (d.severity?.[k]||0)/total : 0;if(!portion)return;const circle=createSvg('circle',{cx:88,cy:88,r:74,fill:'none',stroke:colors[i],'stroke-width':23,'stroke-dasharray':`${portion*465} ${465-portion*465}`,'stroke-dashoffset':`${-offset*465}`,transform:'rotate(-90 88 88)'});svg.appendChild(circle);offset+=portion;});
  ring.prepend(svg);
  drawActivity(d.activity||[]);
}
function createSvg(tag,attrs={}) {const node=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,String(v)));return node;}
function drawActivity(items) {
  const svg=$('activity-chart');svg.replaceChildren();
  const today=new Date();const data=Array.from({length:7},(_,i)=>{const date=new Date(today);date.setDate(today.getDate()-(6-i));const key=date.toISOString().slice(0,10);return {key,day:date.toLocaleDateString([],{weekday:'short'}),count:items.find(x=>x.day===key)?.n||0};});
  const max=Math.max(5,...data.map(x=>x.count)),top=13,bottom=174,left=28,right=611;
  for(let i=0;i<4;i++){const y=top+(bottom-top)*i/3;svg.appendChild(createSvg('line',{x1:left,x2:right,y1:y,y2:y,stroke:'#274054','stroke-dasharray':'3 7'}));const label=createSvg('text',{x:2,y:y+4,fill:'#66849b','font-size':11});label.textContent=Math.round(max*(3-i)/3);svg.appendChild(label);}
  const points=[];data.forEach((item,i)=>{const x=left+(right-left)*i/6;const y=bottom-item.count/max*(bottom-top);points.push([x,y]);const label=createSvg('text',{x,y:199,fill:'#7090a8','font-size':11,'text-anchor':'middle'});label.textContent=item.day;svg.appendChild(label);});
  const area=`M ${points[0][0]} ${bottom} L ${points.map(p=>p.join(' ')).join(' L ')} L ${points.at(-1)[0]} ${bottom} Z`;
  svg.appendChild(createSvg('path',{d:area,fill:'#247e8c','fill-opacity':'.2'}));svg.appendChild(createSvg('path',{d:`M ${points.map(p=>p.join(' ')).join(' L ')}`,fill:'none',stroke:'#5acfd8','stroke-width':3,'stroke-linejoin':'round'}));
  points.forEach(([cx,cy])=>svg.appendChild(createSvg('circle',{cx,cy,r:4,fill:'#6fdbdd',stroke:'#102336','stroke-width':2})));
}
function renderAlerts() {
  const writer=['admin','analyst'].includes(state.user?.role);
  $('alerts-table').innerHTML=state.alerts.map(a=>`<tr><td><strong>${esc(a.title)}</strong><small>#${a.id} · ${esc(a.resource)}</small></td><td>${esc(a.actor)}</td><td><strong>${a.risk_score}/100</strong></td><td>${badge(a.severity)}</td><td>${badge(a.status)}</td><td>${writer&&a.status!=='resolved'?`${a.status==='open'?`<button class="mini-btn" data-alert-id="${a.id}" data-alert-status="investigating">Investigate</button>`:''}<button class="mini-btn" data-alert-id="${a.id}" data-alert-status="resolved">Resolve</button>`:'—'}</td></tr>`).join('')||tdEmpty(6,'No alerts yet.');
}
function renderEvents() {
  const filtered=state.events.filter(e=>state.filter==='all'||e.category===state.filter);
  $('events-table').innerHTML=filtered.map(e=>`<tr><td><strong>#${e.id}</strong><small>${esc(friendly(e.category))}</small></td><td><strong>${esc(friendly(e.kind))}</strong><small>${esc(e.signals.join(', ')||'No risk signals')}</small></td><td>${esc(e.actor)}<small>${esc(e.source_ip)}</small></td><td>${esc(e.resource)}</td><td>${e.risk_score>=70?badge('high'):e.risk_score>=40?badge('medium'):badge('low')} <strong>${e.risk_score}</strong></td><td>${esc(when(e.occurred_at))}</td></tr>`).join('')||tdEmpty(6,'No events match this category.');
}
function renderServices() {
  $('services-grid').innerHTML=state.services.map(s=>`<div class="service-card"><div class="service-head"><div><div class="service-name">${esc(s.name)}</div><small class="muted">${esc(friendly(s.environment))} environment</small></div>${badge(s.status)}</div><div class="service-meta"><div><small>LATENCY</small><strong>${s.latency_ms} ms</strong></div><div><small>ERROR RATE</small><strong>${s.error_rate}%</strong></div><div><small>UPTIME</small><strong>${s.uptime}%</strong></div></div></div>`).join('')||'<div class="no-data">No services yet. Seed demo data to populate infrastructure metrics.</div>';
}
async function renderAudit() {
  if(state.user?.role!=='admin') return;
  try {
    const records=await api('/api/audit');
    $('audit-table').innerHTML=records.map(a=>`<tr><td>#${a.id}</td><td><strong>${esc(a.action)}</strong></td><td>${esc(a.actor)}</td><td>${esc(a.entity)} #${esc(a.entity_id)}</td><td><code>${esc(a.entry_hash.slice(0,12))}…</code></td><td>${esc(when(a.created_at))}</td></tr>`).join('')||tdEmpty(6,'No audit entries yet.');
  }catch(e){errorMessage(e.message)}
}
const scenarios={
  large_transfer:{category:'fintech',kind:'transfer',source_ip:'198.51.100.72',resource:'bank-ledger',amount:22000,currency:'USD',details:{new_payee:true}},
  malware:{category:'cybersecurity',kind:'malware_detected',source_ip:'192.0.2.44',resource:'endpoint-agent',details:{unrecognized_device:true}},
  unauthorized:{category:'cybersecurity',kind:'access_denied',source_ip:'203.0.113.22',resource:'secrets-store',details:{unrecognized_device:true}},
  chargeback:{category:'fintech',kind:'payment_chargeback',source_ip:'198.51.100.22',resource:'card-gateway',amount:950,currency:'USD',details:{}},
  normal:{category:'fintech',kind:'payment',source_ip:'203.0.113.50',resource:'card-gateway',amount:39,currency:'USD',details:{}}
};
document.querySelectorAll('.nav-link').forEach(btn=>btn.addEventListener('click',()=>switchView(btn.dataset.view)));
document.querySelectorAll('[data-jump]').forEach(btn=>btn.addEventListener('click',()=>switchView(btn.dataset.jump)));
document.querySelectorAll('.filter-btn').forEach(btn=>btn.addEventListener('click',()=>{state.filter=btn.dataset.filter;document.querySelectorAll('.filter-btn').forEach(b=>b.classList.toggle('selected',b===btn));renderEvents();}));
$('refresh').addEventListener('click',reload);
$('login-form').addEventListener('submit',async e=>{e.preventDefault();$('login-error').textContent='';try{const user=await api('/api/auth/login',{method:'POST',body:JSON.stringify({email:$('email').value,password:$('password').value})});$('password').value='';showApp(user);await reload();}catch(err){$('login-error').textContent=err.message;}});
$('logout').addEventListener('click',async()=>{try{await api('/api/auth/logout',{method:'POST'});}finally{showLogin();}});
$('alerts-table').addEventListener('click',async e=>{const btn=e.target.closest('[data-alert-id]');if(!btn)return;try{await api(`/api/alerts/${btn.dataset.alertId}`,{method:'PATCH',body:JSON.stringify({status:btn.dataset.alertStatus})});await reload();}catch(err){errorMessage(err.message);}});
$('verify-chain').addEventListener('click',async()=>{try{const result=await api('/api/audit/verify');const el=$('integrity-result');el.className=`integrity-result ${result.valid?'valid':'invalid'}`;el.textContent=result.valid?`✓ Chain verified: ${result.entries} linked entries. Head hash: ${result.head}`:`✕ Integrity failure detected at audit entry #${result.failed_at}.`; }catch(err){errorMessage(err.message)}});
function closeSimulator(){ $('simulator-modal').classList.add('hidden');$('simulator-result').textContent=''; }
$('show-simulator').addEventListener('click',()=>$('simulator-modal').classList.remove('hidden'));
$('close-simulator').addEventListener('click',closeSimulator);$('close-backdrop').addEventListener('click',closeSimulator);
$('simulator-form').addEventListener('submit',async e=>{e.preventDefault();const event={...scenarios[$('event-kind').value],actor:$('event-actor').value.trim()};if(event.actor.length<2)return;try{const result=await api('/api/events',{method:'POST',body:JSON.stringify(event)});$('simulator-result').textContent=`Event #${result.id} processed. Risk score ${result.risk_score}/100 · ${result.severity.toUpperCase()} · ${result.signals.join(', ')||'no risk signals'}.`;await reload();}catch(err){$('simulator-result').textContent=err.message;}});
(async()=>{try{const user=await api('/api/auth/me');showApp(user);await reload();}catch{showLogin();}})();
