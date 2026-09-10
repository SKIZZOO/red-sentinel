const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const state={api:localStorage.getItem("rs_api")||location.origin,token:localStorage.getItem("rs_token")||"",guild:null,guilds:[],logs:[],config:{routes:{}}};
window.rsState=state;
const BUILD="guild-fix-20260911-4";
function toast(t){const e=$("#toast");if(!e)return;e.textContent=t;e.classList.add("show");setTimeout(()=>e.classList.remove("show"),3000)}
function api(path,opts={}){const headers=Object.assign({"Content-Type":"application/json"},opts.headers||{});if(state.token)headers.Authorization=`Bearer ${state.token}`;return fetch(state.api.replace(/\/$/,"")+path,{...opts,headers,cache:"no-store"}).then(async r=>{if(!r.ok)throw new Error((await r.text())||`${r.status} ${r.statusText}`);return r.status===204?{}:r.json()})}
window.navigate=function navigate(v){$$(".view").forEach(x=>x.classList.toggle("active",x.id==="view-"+v));$$(".nav").forEach(x=>x.classList.toggle("active",x.dataset.view===v));$("#pageTitle").textContent=v[0].toUpperCase()+v.slice(1);if(v==="logs")loadLogs();if(v==="overview")loadOverview();if(v==="announce")fillChannels();if(v==="routing")renderRouting()};
async function refreshGuilds(){
 const g=await api("/api/guilds?_build="+encodeURIComponent(BUILD));
 state.guilds=Array.isArray(g)?g:[];
 renderGuilds();
 const current=state.guild&&state.guilds.some(x=>String(x.id)===String(state.guild))?String(state.guild):null;
 state.guild=current||(state.guilds[0]?String(state.guilds[0].id):null);
 if($("#guildSelect"))$("#guildSelect").value=state.guild||"";
 return state.guilds;
}
async function boot(){
 $("#apiUrl").value=state.api;$("#apiToken").value=state.token;
 if(location.hash.startsWith("#token=")){state.token=decodeURIComponent(location.hash.slice(7));localStorage.setItem("rs_token",state.token);history.replaceState({},document.title,location.pathname)}
 if(location.hash.startsWith("#session=")){state.token=decodeURIComponent(location.hash.slice(9));localStorage.setItem("rs_token",state.token);history.replaceState({},document.title,location.pathname)}
 try{await api("/api/health?_build="+encodeURIComponent(BUILD));$("#apiStatus").textContent="API connected";await refreshGuilds();if(state.guild)await loadOverview();else $("#apiStatus").textContent="API connected · no manageable servers"}
 catch(e){$("#apiStatus").textContent="API error";toast("API error: "+e.message)}
}
function renderGuilds(){const s=$("#guildSelect");if(!s)return;s.innerHTML=state.guilds.map(g=>`<option value="${String(g.id)}">${escapeHtml(g.name)} · ${String(g.id)}</option>`).join("")}
async function loadOverview(){
 if(!state.guild)return;
 const gid=String(state.guild);
 // Use the guild object returned by /api/guilds immediately. This makes the
 // dashboard independent of a second guild lookup and prevents stale IDs.
 const listed=state.guilds.find(x=>String(x.id)===gid);
 if(listed)$("#statMembers").textContent=listed.member_count??"—";
 try{
   const g=await api(`/api/guilds/${gid}?_build=${encodeURIComponent(BUILD)}`);
   if(g){$("#statMembers").textContent=g.member_count??listed?.member_count??"—";fillChannels(g.channels)}
 }catch(e){if(!listed)$("#statMembers").textContent="—";console.warn("Guild details failed",e)}
 try{
   state.logs=await api(`/api/guilds/${gid}/events?limit=500&_build=${encodeURIComponent(BUILD)}`);renderLogs();
 }catch(e){state.logs=[];console.warn("Guild events failed",e)}
 try{
   state.config=await api(`/api/guilds/${gid}/config?_build=${encodeURIComponent(BUILD)}`);state.config=state.config||{routes:{}};
 }catch(e){state.config={providers:{},routes:{}};console.warn("Guild config failed",e)}
 $("#statEvents").textContent=state.logs.filter(x=>Number(x.created_at)>=Math.floor(new Date().setHours(0,0,0,0)/1000)).length;
 $("#statRoutes").textContent=Object.keys(state.config.routes||{}).length;
 $("#activity").innerHTML=state.logs.slice(0,8).map(logRow).join("")||`<div class="hint">No events yet. Activity will appear as the bot observes your server.</div>`;
 $("#routeCards").innerHTML=["twitch","youtube","kick","x"].map(p=>`<div class="route"><b>${p.toUpperCase()}</b><i>${state.config.routes?.[p]?"● ROUTED":"○ NOT ROUTED"}</i></div>`).join("");
}
async function loadLogs(){if(!state.guild)return;try{state.logs=await api(`/api/guilds/${String(state.guild)}/events?limit=500${$("#logType").value?"&type="+encodeURIComponent($("#logType").value):""}&_build=${encodeURIComponent(BUILD)}`);renderLogs()}catch(e){toast("Logs failed: "+e.message)}}
function renderLogs(){const q=$("#logSearch").value.toLowerCase();$("#logTable").innerHTML=state.logs.filter(x=>JSON.stringify(x).toLowerCase().includes(q)).map(x=>`<tr><td>${time(x.created_at)}</td><td><span class="tag">${escapeHtml(x.type)}</span></td><td>${escapeHtml(x.actor_name||"System")}</td><td>${escapeHtml(x.channel_name||"—")}</td><td>${escapeHtml(detail(x))}</td></tr>`).join("")}
function logRow(x){return `<div class="activity-row"><div class="dot"></div><div><b>${escapeHtml(x.type)}</b><br><small>${escapeHtml(x.actor_name||"System")} ${x.channel_name?"in #"+escapeHtml(x.channel_name):""}</small></div><small>${time(x.created_at)}</small></div>`}
function detail(x){const p=x.payload||{};return p.content||p.reason||p.after||p.message_id||"Event received"}
function time(s){return new Date(s*1000).toLocaleString([], {month:"short",day:"2-digit",hour:"2-digit",minute:"2-digit"})}
function fillChannels(channels){if(!channels)return;const chans=channels.filter(c=>c.type==="text").map(c=>`<option value="${c.id}"># ${escapeHtml(c.name)}</option>`).join("");$("#announceChannel").innerHTML=chans;renderRouting(channels)}
async function moderate(action){try{const body={user_id:$("#modUser").value,reason:$("#modReason").value};if(action==="timeout")body.minutes=60;await api(`/api/guilds/${String(state.guild)}/moderation/${action}`,{method:"POST",body:JSON.stringify(body)});toast(`${action} completed`);loadLogs();loadOverview()}catch(e){toast("Action failed: "+e.message)}}
async function sendAnnouncement(){try{const color=parseInt($("#embedColor").value.replace("#",""),16)||0x7c5cfc;const embed={title:$("#embedTitle").value,description:$("#embedDescription").value,color,image:$("#embedImage").value};await api(`/api/guilds/${String(state.guild)}/announce`,{method:"POST",body:JSON.stringify({channel_id:$("#announceChannel").value,content:$("#announceContent").value,embed})});toast("Announcement published");$("#announceContent").value="";loadOverview()}catch(e){toast("Publish failed: "+e.message)}}
async function renderRouting(channels){if(!channels){try{channels=(await api(`/api/guilds/${String(state.guild)}?_build=${encodeURIComponent(BUILD)}`)).channels}catch(e){toast("Channels failed: "+e.message);return}}const texts=channels.filter(c=>c.type==="text");$("#routingForm").innerHTML=["twitch","youtube","kick","x","custom"].map(p=>`<label>${p.toUpperCase()} destination<select data-route="${p}"><option value="">Disabled</option>${texts.map(c=>`<option value="${c.id}" ${state.config.routes?.[p]==c.id?"selected":""}># ${escapeHtml(c.name)}</option>`).join("")}</select></label>`).join("")}
async function saveRouting(){const routes={};$$('[data-route]').forEach(s=>{if(s.value)routes[s.dataset.route]=s.value});try{await api(`/api/guilds/${String(state.guild)}/config`,{method:"PUT",body:JSON.stringify({routes})});toast("Routing saved");loadOverview()}catch(e){toast("Save failed: "+e.message)}}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
window.refreshGuilds=refreshGuilds;window.loadOverview=loadOverview;window.loadLogs=loadLogs;window.renderLogs=renderLogs;window.fillChannels=fillChannels;window.renderRouting=renderRouting;window.moderate=moderate;window.sendAnnouncement=sendAnnouncement;window.saveRouting=saveRouting;
$("#saveConnection").onclick=()=>{state.api=$("#apiUrl").value.trim()||location.origin;state.token=$("#apiToken").value.trim();localStorage.setItem("rs_api",state.api);localStorage.setItem("rs_token",state.token);boot()};
$("#oauthLogin").onclick=()=>{state.api=$("#apiUrl").value.trim()||location.origin;localStorage.setItem("rs_api",state.api);location.href=state.api.replace(/\/$/,"")+"/oauth/discord/start"};
$("#refreshBtn").onclick=async()=>{try{await refreshGuilds();await loadOverview()}catch(e){toast("Refresh failed: "+e.message)}};
$("#logRefresh").onclick=()=>loadLogs();$("#logType").onchange=loadLogs;$("#logSearch").oninput=renderLogs;$("#sendAnnounce").onclick=sendAnnouncement;$("#saveRouting").onclick=saveRouting;
$("#guildSelect").onchange=()=>{state.guild=String($("#guildSelect").value||"");loadOverview()};
console.info("Red Sentinel dashboard",BUILD);
boot();
