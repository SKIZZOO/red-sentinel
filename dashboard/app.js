const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const state={api:localStorage.getItem("rs_api")||"",token:localStorage.getItem("rs_token")||"",guild:null,guilds:[],logs:[],config:{}};
function toast(t){const e=$("#toast");e.textContent=t;e.classList.add("show");setTimeout(()=>e.classList.remove("show"),2500)}
function api(path,opts={}){const headers=Object.assign({"Content-Type":"application/json"},opts.headers||{});if(state.token)headers.Authorization=`Bearer ${state.token}`;return fetch(state.api.replace(/\/$/,"")+path,{...opts,headers}).then(async r=>{if(!r.ok)throw new Error(await r.text()||r.statusText);return r.status===204?{}:r.json()})}
function navigate(v){$$(".view").forEach(x=>x.classList.toggle("active",x.id==="view-"+v));$$(".nav").forEach(x=>x.classList.toggle("active",x.dataset.view===v));$("#pageTitle").textContent=v[0].toUpperCase()+v.slice(1);if(v==="logs")loadLogs();if(v==="overview")loadOverview();if(v==="announce")fillChannels();if(v==="routing")renderRouting()}
window.navigate=navigate;
async function boot(){
 $("#apiUrl").value=state.api;$("#apiToken").value=state.token;
 if(location.hash.startsWith("#token=")){state.token=decodeURIComponent(location.hash.slice(7));localStorage.setItem("rs_token",state.token);history.replaceState({},document.title,location.pathname)}
 if(!state.api){$("#apiStatus").textContent="Set API URL in Settings";return}
 try{await api("/api/health");$("#apiStatus").textContent="API connected";const g=await api("/api/guilds");state.guilds=g;renderGuilds();if(g[0]){state.guild=g[0].id;$("#guildSelect").value=g[0].id;await loadOverview()}}catch(e){$("#apiStatus").textContent="API unavailable";toast("Connect the dashboard to your Sentinel API")}
}
function renderGuilds(){const s=$("#guildSelect");s.innerHTML=state.guilds.map(g=>`<option value="${g.id}">${escapeHtml(g.name)}</option>`).join("")}
async function loadOverview(){
 if(!state.guild)return;const [g,logs,cfg]=await Promise.all([api(`/api/guilds/${state.guild}`),api(`/api/guilds/${state.guild}/events?limit=12`),api(`/api/guilds/${state.guild}/config`)]);
 state.logs=logs;state.config=cfg;$("#statMembers").textContent=g.member_count??"—";$("#statEvents").textContent=logs.length;$("#statRoutes").textContent=Object.keys(cfg.routes||{}).length;
 $("#activity").innerHTML=logs.slice(0,8).map(logRow).join("")||`<div class="hint">No events yet. Activity will appear as the bot observes your server.</div>`;
 $("#routeCards").innerHTML=["twitch","youtube","kick","x"].map(p=>`<div class="route"><b>${p.toUpperCase()}</b><i>${cfg.routes?.[p]?"● ROUTED":"○ NOT ROUTED"}</i></div>`).join("");
 fillChannels(g.channels);
}
async function loadLogs(){
 if(!state.guild)return;state.logs=await api(`/api/guilds/${state.guild}/events?limit=250${$("#logType").value?"&type="+encodeURIComponent($("#logType").value):""}`);
 renderLogs();
}
function renderLogs(){const q=$("#logSearch").value.toLowerCase();$("#logTable").innerHTML=state.logs.filter(x=>JSON.stringify(x).toLowerCase().includes(q)).map(x=>`<tr><td>${time(x.created_at)}</td><td><span class="tag">${escapeHtml(x.type)}</span></td><td>${escapeHtml(x.actor_name||"System")}</td><td>${escapeHtml(x.channel_name||"—")}</td><td>${escapeHtml(detail(x))}</td></tr>`).join("")}
function logRow(x){return `<div class="activity-row"><div class="dot"></div><div><b>${escapeHtml(x.type)}</b><br><small>${escapeHtml(x.actor_name||"System")} ${x.channel_name?"in #"+escapeHtml(x.channel_name):""}</small></div><small>${time(x.created_at)}</small></div>`}
function detail(x){const p=x.payload||{};return p.content||p.reason||p.after||p.message_id||"Event received"}
function time(s){return new Date(s*1000).toLocaleString([], {month:"short",day:"2-digit",hour:"2-digit",minute:"2-digit"})}
function fillChannels(channels){if(!channels)return;const chans=channels.filter(c=>c.type==="text").map(c=>`<option value="${c.id}"># ${escapeHtml(c.name)}</option>`).join("");$("#announceChannel").innerHTML=chans;renderRouting(channels)}
async function moderate(action){try{const body={user_id:$("#modUser").value,reason:$("#modReason").value};if(action==="timeout")body.seconds=3600;await api(`/api/guilds/${state.guild}/moderation/${action}`,{method:"POST",body:JSON.stringify(body)});toast(`${action} completed`);loadLogs()}catch(e){toast("Action failed: "+e.message)}}
async function sendAnnouncement(){try{const color=parseInt($("#embedColor").value.replace("#",""),16)||0x7c5cfc;const embed={title:$("#embedTitle").value,description:$("#embedDescription").value,color,image:$("#embedImage").value};await api(`/api/guilds/${state.guild}/announce`,{method:"POST",body:JSON.stringify({channel_id:$("#announceChannel").value,content:$("#announceContent").value,embed})});toast("Announcement published");$("#announceContent").value=""}catch(e){toast("Publish failed: "+e.message)}}
async function renderRouting(channels){if(!channels){try{channels=(await api(`/api/guilds/${state.guild}`)).channels}catch{return}}const texts=channels.filter(c=>c.type==="text");$("#routingForm").innerHTML=["twitch","youtube","kick","x","custom"].map(p=>`<label>${p.toUpperCase()} destination<select data-route="${p}"><option value="">Disabled</option>${texts.map(c=>`<option value="${c.id}" ${state.config.routes?.[p]==c.id?"selected":""}># ${escapeHtml(c.name)}</option>`).join("")}</select></label>`).join("")}
async function saveRouting(){const routes={};$$("[data-route]").forEach(s=>{if(s.value)routes[s.dataset.route]=s.value});try{await api(`/api/guilds/${state.guild}/config`,{method:"PUT",body:JSON.stringify({routes})});toast("Routing saved");loadOverview()}catch(e){toast("Save failed: "+e.message)}}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
$("#saveConnection").onclick=()=>{state.api=$("#apiUrl").value.trim();state.token=$("#apiToken").value.trim();localStorage.setItem("rs_api",state.api);localStorage.setItem("rs_token",state.token);boot()}
$("#oauthLogin").onclick=()=>{if(!state.api)return toast("Set API URL first");location.href=state.api.replace(/\/$/,"")+"/oauth/discord/start"}
$("#refreshBtn").onclick=()=>loadOverview();$("#logRefresh").onclick=()=>loadLogs();$("#logType").onchange=loadLogs;$("#logSearch").oninput=renderLogs;$("#sendAnnounce").onclick=sendAnnouncement;$("#saveRouting").onclick=saveRouting;
$("#guildSelect").onchange=()=>{state.guild=Number($("#guildSelect").value);loadOverview()}
$$(".nav").forEach(b=>b.onclick=()=>navigate(b.dataset.view));boot();
