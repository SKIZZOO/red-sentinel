(()=>{
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state=window.rsState; if(!state)return;
let members=[],selected=null;
const api=(path,opts={})=>{const h=Object.assign({'Content-Type':'application/json'},opts.headers||{});if(state.token)h.Authorization=`Bearer ${state.token}`;return fetch(state.api.replace(/\/$/,'')+path,{...opts,headers:h,cache:'no-store'}).then(async r=>{if(!r.ok)throw new Error((await r.text())||`${r.status} ${r.statusText}`);return r.status===204?{}:r.json()})};
const toast=t=>window.toast?window.toast(t):(()=>{const e=$('#toast');if(e){e.textContent=t;e.classList.add('show');setTimeout(()=>e.classList.remove('show'),3000)}})();
const gid=()=>String(state.guild||'');
function renderSelect(list){const s=$('#modMemberSelect');if(!s)return;s.innerHTML='<option value="">Select a member…</option>'+list.map(m=>`<option value="${esc(m.id)}">${esc(m.display_name||m.name)} · @${esc(m.name)}</option>`).join('');if(selected)s.value=String(selected.id)}
function renderCard(m){const card=$('#modMemberCard');if(!card)return;if(!m){card.hidden=true;card.innerHTML='';return}card.hidden=false;card.innerHTML=`<div class="mod-member-avatar-wrap"><img class="mod-member-avatar" src="${esc(m.avatar||'')}" alt="" onerror="this.style.visibility='hidden'"></div><div class="mod-member-main"><div class="mod-member-name"><strong>${esc(m.display_name||m.name)}</strong>${m.bot?'<span class="mod-bot">BOT</span>':''}</div><span class="mod-member-username">@${esc(m.name)} · ${esc(m.id)}</span><div class="mod-member-roles">${(m.roles||[]).map(r=>`<span style="--role-color:${esc(r.color||'#a78bfa')}">${esc(r.name)}</span>`).join('')||'<em>No roles</em>'}</div><div class="mod-member-meta"><span>${m.timeout_until?'⏳ Timed out':'● Active'}</span><span>${m.joined_at?'Joined '+new Date(m.joined_at).toLocaleDateString():'Join date unknown'}</span></div></div>`}
function selectMember(id){selected=members.find(m=>String(m.id)===String(id))||null;const input=$('#modUser');if(input)input.value=selected?String(selected.id):'';renderCard(selected)}
async function load(){if(!gid())return;try{const data=await api(`/api/guilds/${gid()}/members?limit=500`);members=data.members||[];const q=($('#modMemberSearch')?.value||'').trim().toLowerCase();renderSelect(q?members.filter(m=>`${m.display_name} ${m.name} ${m.id}`.toLowerCase().includes(q)):members);if(selected)selectMember(selected.id)}catch(e){toast('Moderation members failed: '+e.message)}}
async function action(name){const uid=String($('#modUser')?.value||'').trim();if(!uid)return toast('Select a member first.');const reason=String($('#modReason')?.value||'').trim()||'Red Sentinel moderation';try{const body={user_id:uid,reason};if(name==='timeout')body.minutes=60;await api(`/api/guilds/${gid()}/moderation/${name}`,{method:'POST',body:JSON.stringify(body)});toast(`${name} completed`);await load();if(selected)selectMember(selected.id);await window.loadLogs?.()}catch(e){toast('Action failed: '+e.message)}}
function bind(){
 $('#modMemberSelect')?.addEventListener('change',e=>selectMember(e.target.value));
 let t;$('#modMemberSearch')?.addEventListener('input',()=>{clearTimeout(t);t=setTimeout(load,180)});
 $('#modRefreshMembers')?.addEventListener('click',load);
 $('#modUser')?.addEventListener('input',e=>{const m=members.find(x=>String(x.id)===String(e.target.value).trim());if(m){selected=m;renderCard(m)}else if(!e.target.value)selectMember('')});
 $('.nav[data-view="moderation"]')?.addEventListener('click',()=>setTimeout(load,50));
 $('#guildSelect')?.addEventListener('change',()=>setTimeout(load,120));
 $('#modSelectClear')?.addEventListener('click',()=>selectMember(''));
 window.loadModerationMembers=load;
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
