(()=>{
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>\"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;","'":'&#39;'}[c]));
const names={
 'message.create':'Message sent','message.edit':'Message edited','message.delete':'Message deleted',
 'member.join':'Member joined','member.leave':'Member left','member.nickname':'Nickname changed',
 'voice.update':'Voice activity','channel.create':'Channel created','channel.delete':'Channel deleted','channel.update':'Channel updated',
 'role.create':'Role created','role.delete':'Role deleted','role.update':'Role updated',
 'admin.announce':'Announcement published','admin.ban':'Member banned','admin.kick':'Member kicked','admin.timeout':'Member timed out','admin.delete':'Message deleted',
 'social.twitch':'Twitch signal','social.youtube':'YouTube signal','social.kick':'Kick signal','social.x':'X signal'
};
const icons={message:'✦',member:'♙',voice:'◉',channel:'#',role:'◆',admin:'⚔',social:'◎'};
const friendly=t=>names[t]||String(t||'System event').replaceAll('.',' · ');
const icon=t=>icons[String(t||'').split('.')[0]]||'•';
const detail=x=>{const p=x.payload||{};if(p.content)return p.content;if(p.reason)return `Reason: ${p.reason}`;if(p.after)return `Changed to: ${p.after}`;if(p.before&&p.after)return `${p.before} → ${p.after}`;if(p.title)return p.title;if(p.message_id)return `Message ID ${p.message_id}`;return 'Event received by Red Sentinel'};
function enhance(){
 const activity=$('#activity');if(activity){
   const old=activity.innerHTML;
   if(old&&old.includes('activity-row')){
     // Re-render from the same state exposed by the dashboard, keeping live data authoritative.
     const logs=window.rsState?.logs||[];
     activity.innerHTML=logs.slice(0,8).map(x=>`<div class="activity-row"><div class="dot" data-kind="${esc(String(x.type||'').split('.')[0])}">${icon(x.type)}</div><div><b>${esc(friendly(x.type))}</b><div class="activity-meta"><span class="activity-event">${esc(x.type||'event')}</span>${x.channel_name?`<span class="activity-channel">#${esc(x.channel_name)}</span>`:''}${x.actor_name?`<span class="activity-channel">by ${esc(x.actor_name)}</span>`:''}</div><span class="activity-detail">${esc(detail(x))}</span></div><small>${window.time?window.time(x.created_at):new Date(x.created_at*1000).toLocaleString([], {month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</small></div>`).join('')||old;
   }
 }
 const logsView=$('#view-logs');if(logsView&&!logsView.dataset.enhanced){
   logsView.dataset.enhanced='1';
   const toolbar=logsView.querySelector('.toolbar');
   if(toolbar){toolbar.classList.add('logs-toolbar');
     const head=document.createElement('div');head.className='logs-head';head.innerHTML='<div><span class="eyebrow">AUDIT STREAM</span><h2>Live logs</h2><p>Every important server action in one clear timeline. Filter events, identify who acted and see what changed.</p></div><span class="logs-live-badge"><i></i> LIVE MONITORING</span>';
     toolbar.parentNode.insertBefore(head,toolbar);
   }
   const panel=logsView.querySelector('.table-wrap');if(panel){panel.classList.add('logs-panel','logs-table-wrap');const table=panel.querySelector('table');if(table)table.classList.add('logs-table')}
 }
}
function renderEnhanced(){
 const table=$('#logTable');if(!table)return;
 const state=window.rsState||{};const q=($('#logSearch')?.value||'').toLowerCase();
 const logs=(state.logs||[]).filter(x=>JSON.stringify(x).toLowerCase().includes(q));
 table.innerHTML=logs.map(x=>`<tr><td>${window.time?window.time(x.created_at):new Date(x.created_at*1000).toLocaleString()}</td><td><span class="logs-event"><span class="logs-event-dot"></span>${esc(friendly(x.type))}</span></td><td>${esc(x.actor_name||'System')}</td><td>${x.channel_name?`<span class="logs-channel">${esc(x.channel_name)}</span>`:'—'}</td><td><span class="logs-detail">${esc(detail(x))}</span></td></tr>`).join('')||'<tr><td colspan="5"><div class="hint" style="padding:28px">No matching events found.</div></td></tr>';
}
const original=window.renderLogs;
window.renderLogs=()=>{original?.();enhance();renderEnhanced()};
const oldOverview=window.loadOverview;window.loadOverview=async(...a)=>{const r=await oldOverview?.(...a);enhance();return r};
const oldLoadLogs=window.loadLogs;window.loadLogs=async(...a)=>{const r=await oldLoadLogs?.(...a);enhance();renderEnhanced();return r};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(enhance,80),{once:true});else setTimeout(enhance,80);
})();
