(()=>{
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>\"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;","'":'&#39;'}[c]));
const names={'message.create':'Message sent','message.edit':'Message edited','message.delete':'Message deleted','member.join':'Member joined','member.leave':'Member left','member.nickname':'Nickname changed','voice.update':'Voice activity','channel.create':'Channel created','channel.delete':'Channel deleted','channel.update':'Channel updated','role.create':'Role created','role.delete':'Role deleted','role.update':'Role updated','admin.announce':'Announcement published','admin.ban':'Member banned','admin.kick':'Member kicked','admin.timeout':'Member timed out','admin.delete':'Message deleted','admin.chat_send':'Dashboard message sent','admin.chat_delete':'Dashboard message deleted','social.twitch':'Twitch signal','social.youtube':'YouTube signal','social.kick':'Kick signal','social.x':'X signal'};
const icons={message:'✦',member:'♙',voice:'◉',channel:'#',role:'◆',admin:'⚔',social:'◎'};
const friendly=t=>names[t]||String(t||'System event').replaceAll('.',' · ');
const icon=t=>icons[String(t||'').split('.')[0]]||'•';
const detail=x=>{const p=x.payload||{};if(p.content)return p.content;if(p.reason)return `Reason: ${p.reason}`;if(p.before!==undefined&&p.after!==undefined)return `${p.before||'—'} → ${p.after||'—'}`;if(p.title)return p.title;if(p.message_id)return `Message ID ${p.message_id}`;if(p.name)return p.name;return 'Event received by Red Sentinel'};
const avatar=x=>x.actor_avatar||x.target_avatar||'';
const actor=x=>x.actor_display_name||x.actor_name||'System';
const actionButton=(label,cls,action)=>`<button type="button" class="log-action ${cls||''}" data-log-action="${action}">${label}</button>`;
function openDetails(x){
 let modal=$('#logDetailModal');if(!modal){modal=document.createElement('div');modal.id='logDetailModal';modal.className='log-modal';document.body.appendChild(modal)}
 const p=x.payload||{}, av=avatar(x), target=x.target_display_name||x.target_name;
 modal.innerHTML=`<div class="log-modal-backdrop" data-log-close></div><div class="log-modal-card"><div class="log-modal-top"><div class="log-user">${av?`<img src="${esc(av)}" alt="">`:'<div class="log-avatar-fallback">✦</div>'}<div><strong>${esc(actor(x))}</strong><span>${esc(x.actor_id||'System')}</span></div></div><button type="button" class="log-modal-close" data-log-close>×</button></div><div class="log-modal-event"><span class="logs-event"><span class="logs-event-dot"></span>${esc(friendly(x.type))}</span><time>${esc(window.time?window.time(x.created_at):new Date(x.created_at*1000).toLocaleString())}</time></div><div class="log-detail-body"><div><small>CHANNEL</small><b>${x.channel_name?`#${esc(x.channel_name)}`:'System'}</b></div>${target?`<div><small>TARGET</small><b>${esc(target)}</b></div>`:''}<div><small>DETAIL</small><p>${esc(detail(x))}</p></div><div><small>EVENT ID</small><code>${esc(x.id||'—')}</code></div>${x.message_url?`<div><small>DISCORD MESSAGE</small><a href="${esc(x.message_url)}" target="_blank" rel="noreferrer">Open original message ↗</a></div>`:''}<div><small>RAW PAYLOAD</small><pre>${esc(JSON.stringify(p,null,2))}</pre></div></div><div class="log-modal-actions">${x.message_url?actionButton('Open in Discord','primary','open'):''}${p.message_id&&x.channel_id?actionButton('Delete message','danger','delete'):''}${x.actor_id?actionButton('Copy user ID','ghost','copy-user'):''}${x.channel_id?actionButton('Copy channel ID','ghost','copy-channel'):''}${p.message_id?actionButton('Copy message ID','ghost','copy-message'):''}${x.actor_id?actionButton('Filter actor','ghost','filter-actor'):''}</div></div>`;
 modal.classList.add('open');modal._log=x;
}
function closeModal(){const m=$('#logDetailModal');if(m)m.classList.remove('open')}
async function handleAction(btn){
 const m=$('#logDetailModal'),x=m?m._log:null;if(!x)return;const action=btn.dataset.logAction,p=x.payload||{};
 if(action==='open'&&x.message_url){window.open(x.message_url,'_blank','noopener');return}
 if(action==='copy-user'){await navigator.clipboard?.writeText(String(x.actor_id||''));toast('User ID copied');return}
 if(action==='copy-channel'){await navigator.clipboard?.writeText(String(x.channel_id||''));toast('Channel ID copied');return}
 if(action==='copy-message'){await navigator.clipboard?.writeText(String(p.message_id||''));toast('Message ID copied');return}
 if(action==='filter-actor'){const s=$('#logSearch');if(s){s.value=String(x.actor_name||x.actor_display_name||'');closeModal();renderEnhanced()}return}
 if(action==='delete'&&p.message_id&&x.channel_id){
   if(!confirm('Delete this Discord message?'))return;
   try{await api(`/api/guilds/${String(window.rsState.guild)}/channels/${String(x.channel_id)}/messages/${String(p.message_id)}`,{method:'DELETE'});toast('Message deleted');closeModal();await window.loadLogs?.()}catch(e){toast('Delete failed: '+e.message)}
 }
}
function enhance(){
 const logsView=$('#view-logs');if(!logsView)return;
 if(!logsView.dataset.enhanced){logsView.dataset.enhanced='1';const toolbar=logsView.querySelector('.toolbar');if(toolbar){toolbar.classList.add('logs-toolbar');const head=document.createElement('div');head.className='logs-head';head.innerHTML='<div><span class="eyebrow">AUDIT STREAM</span><h2>Live logs</h2><p>Every important server action in one clear timeline. Inspect the actor, open the original message, remove it, or run quick actions.</p></div><span class="logs-live-badge"><i></i> LIVE MONITORING</span>';toolbar.parentNode.insertBefore(head,toolbar)}const panel=logsView.querySelector('.table-wrap');if(panel){panel.classList.add('logs-panel','logs-table-wrap');const table=panel.querySelector('table');if(table)table.classList.add('logs-table')}}
}
function renderEnhanced(){
 const table=$('#logTable');if(!table)return;enhance();const state=window.rsState||{};const q=($('#logSearch')?.value||'').toLowerCase();const logs=(state.logs||[]).filter(x=>JSON.stringify(x).toLowerCase().includes(q));
 table.innerHTML=logs.map(x=>{const p=x.payload||{},av=avatar(x);return `<tr><td>${window.time?window.time(x.created_at):new Date(x.created_at*1000).toLocaleString()}</td><td><span class="logs-event"><span class="logs-event-dot"></span>${esc(friendly(x.type))}</span></td><td><div class="log-actor"><div class="log-avatar">${av?`<img src="${esc(av)}" alt="">`:'✦'}</div><div><b>${esc(actor(x))}</b><small>${esc(x.actor_id||'System')}</small></div></div></td><td>${x.channel_name?`<span class="logs-channel">${esc(x.channel_name)}</span>`:'—'}</td><td><span class="logs-detail">${esc(detail(x))}</span></td><td class="logs-actions">${actionButton('View','ghost','view')}${p.message_id&&x.channel_id?actionButton('Delete','danger','delete-row'):''}<button type="button" class="log-more" data-log-more="1">•••</button></td></tr>`}).join('')||'<tr><td colspan="6"><div class="hint" style="padding:28px">No matching events found.</div></td></tr>';
 [...table.querySelectorAll('[data-log-action="view"]')].forEach((b,i)=>b.addEventListener('click',()=>openDetails(logs[i])));
 [...table.querySelectorAll('[data-log-action="delete-row"]')].forEach((b,i)=>b.addEventListener('click',async()=>{const x=logs[i],p=x.payload||{};if(!confirm('Delete this Discord message?'))return;try{await api(`/api/guilds/${String(state.guild)}/channels/${String(x.channel_id)}/messages/${String(p.message_id)}`,{method:'DELETE'});toast('Message deleted');await window.loadLogs?.()}catch(e){toast('Delete failed: '+e.message)}}));
 [...table.querySelectorAll('[data-log-more]')].forEach((b,i)=>b.addEventListener('click',e=>{e.stopPropagation();openDetails(logs[i])}));
}
const original=window.renderLogs;window.renderLogs=()=>{original?.();renderEnhanced()};
const oldLoadLogs=window.loadLogs;window.loadLogs=async(...a)=>{const r=await oldLoadLogs?.(...a);renderEnhanced();return r};
const oldOverview=window.loadOverview;window.loadOverview=async(...a)=>{const r=await oldOverview?.(...a);renderEnhanced();return r};
document.addEventListener('click',e=>{if(e.target.closest('[data-log-close]'))closeModal();const b=e.target.closest('.log-modal-actions [data-log-action]');if(b)handleAction(b)});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(renderEnhanced,80),{once:true});else setTimeout(renderEnhanced,80);
})();
