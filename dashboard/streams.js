(() => {
  const $ = s => document.querySelector(s);
  const api = window.api || ((path, opts={}) => { const h={'Content-Type':'application/json'}; const t=localStorage.getItem('rs_token')||''; if(t) h.Authorization=`Bearer ${t}`; return fetch((localStorage.getItem('rs_api')||location.origin).replace(/\/$/,'')+path,{...opts,headers:h,cache:'no-store'}).then(async r=>{if(!r.ok)throw new Error((await r.text())||`${r.status} ${r.statusText}`);return r.json()}) });
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const toast = t => window.toast ? window.toast(t) : (()=>{const e=$('#toast');if(e){e.textContent=t;e.classList.add('show');setTimeout(()=>e.classList.remove('show'),3000)}})();
  const platformSvg = {
    twitch:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 3h17v12l-5 5h-4l-3 3v-3H4z"/><path fill="rgba(8,7,14,.92)" d="M9 8h2v5H9zm5 0h2v5h-2z"/></svg>',
    youtube:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21 7.2a2.8 2.8 0 0 0-2-2C17.2 4.7 12 4.7 12 4.7s-5.2 0-7 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2.5 12 29 29 0 0 0 3 16.8a2.8 2.8 0 0 0 2 2c1.8.5 7 .5 7 .5s5.2 0 7-.5a2.8 2.8 0 0 0 2-2 29 29 0 0 0 .5-4.8 29 29 0 0 0-.5-4.8Z"/><path fill="rgba(8,7,14,.92)" d="m10 9 5 3-5 3z"/></svg>',
    kick:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 4h6v5l4-5h6l-6 8 6 8h-6l-4-5v5H4z"/></svg>',
    x:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M5 4h4.7l3.2 4.5L16.7 4H20l-5.5 6.3L21 20h-4.7l-3.7-5.2L8.1 20H5l5.7-6.6z"/></svg>'
  };
  function platformIcon(p, cls=''){ const key=(p||'').toLowerCase(); return `<span class="stream-platform-icon ${esc(key)} ${cls}">${platformSvg[key]||''}</span>`; }
  function gid(){ return String(window.rsState?.guild || ''); }
  async function loadStreams(){
    if(!gid()) return;
    try{
      const [data,g] = await Promise.all([api(`/api/guilds/${gid()}/streams`), api(`/api/guilds/${gid()}`)]);
      const channels=(g.channels||[]).filter(c=>c.type==='text');
      const sel=$('#streamChannel'); if(sel) sel.innerHTML=channels.map(c=>`<option value="${String(c.id)}"># ${esc(c.name)}</option>`).join('');
      const s=data.sources||[], st=data.settings||{};
      if($('#streamDefaultTitle')) $('#streamDefaultTitle').value=st.title||'🔴 {name} is LIVE!';
      if($('#streamDefaultColor')) $('#streamDefaultColor').value=st.color||'9146FF';
      if($('#streamDefaultMessage')) $('#streamDefaultMessage').value=st.message||'{name} just went live on {platform}. Come hang out!';
      if($('#streamDedupe')) $('#streamDedupe').checked=st.dedupe!==false;
      render(s); if($('#streamCount')) $('#streamCount').textContent=`${s.length} source${s.length===1?'':'s'}`;
    }catch(e){ toast('Livestreams failed: '+e.message); }
  }
  function render(items){
    const box=$('#streamList'); if(!box)return;
    if(!items.length){box.innerHTML='<div class="stream-empty"><div class="empty-icon">◉</div><b>No livestream sources yet</b><span>Add a Twitch, YouTube or Kick channel and choose a Discord destination.</span></div>';return;}
    box.innerHTML=items.map(x=>`<div class="stream-item ${x.enabled?'':'disabled'}"><div class="stream-brand ${esc(x.platform)}">${platformIcon(x.platform)}</div><div class="stream-main"><div class="stream-name"><b>${esc(x.name)}</b><span class="live-pill ${x.live?'is-live':''}">${x.live?'● LIVE':x.enabled?'● MONITORING':'○ PAUSED'}</span></div><div class="stream-platform-name">${esc((x.platform||'').toUpperCase())}</div><small>${esc(x.url)}</small><small>→ Discord channel ${esc(x.channel_id)}</small></div><div class="stream-actions"><button class="ghost stream-toggle" data-id="${esc(x.id)}">${x.enabled?'Pause':'Resume'}</button><button class="danger stream-delete" data-id="${esc(x.id)}">Remove</button></div></div>`).join('');
    box.querySelectorAll('.stream-toggle').forEach(b=>b.onclick=()=>action('toggle',b.dataset.id));
    box.querySelectorAll('.stream-delete').forEach(b=>b.onclick=()=>action('delete',b.dataset.id));
  }
  async function action(action,id){try{const r=await api(`/api/guilds/${gid()}/streams`,{method:'POST',body:JSON.stringify({action,id})});render(r.sources||[]);if($('#streamCount'))$('#streamCount').textContent=`${(r.sources||[]).length} sources`;toast(action==='delete'?'Livestream removed':`Livestream ${action==='toggle'?'updated':'saved'}`)}catch(e){toast('Livestream action failed: '+e.message)}}
  async function add(){
    const url=$('#streamUrl')?.value.trim()||''; if(!url)return toast('Add a livestream URL first.');
    try{const r=await api(`/api/guilds/${gid()}/streams`,{method:'POST',body:JSON.stringify({action:'add',platform:$('#streamPlatform')?.value,name:$('#streamName')?.value,url,channel_id:$('#streamChannel')?.value,title:$('#streamTitle')?.value,image:$('#streamImage')?.value,mention_everyone:$('#streamMention')?.checked})});render(r.sources||[]);$('#streamUrl').value='';$('#streamName').value='';$('#streamTitle').value='';$('#streamImage').value='';$('#streamMention').checked=false;if($('#streamCount'))$('#streamCount').textContent=`${(r.sources||[]).length} sources`;toast('Livestream source added. Monitoring is active.')}catch(e){toast('Could not add livestream: '+e.message)}
  }
  async function saveSettings(){try{await api(`/api/guilds/${gid()}/streams/settings`,{method:'PUT',body:JSON.stringify({title:$('#streamDefaultTitle')?.value,message:$('#streamDefaultMessage')?.value,color:$('#streamDefaultColor')?.value,dedupe:$('#streamDedupe')?.checked})});toast('Livestream notification settings saved.')}catch(e){toast('Settings failed: '+e.message)}}
  function boot(){
    $('#addStream')?.addEventListener('click',add); $('#saveStreamSettings')?.addEventListener('click',saveSettings);
    const old=window.showView;
    if(old && !window.__streamViewPatched){ window.__streamViewPatched=true; window.showView=async v=>{const r=old(v);if(v==='streams')await loadStreams();return r}; window.navigate=window.showView; }
    document.addEventListener('change',e=>{if(e.target?.id==='guildSelect' && $('#view-streams')?.classList.contains('active'))setTimeout(loadStreams,150)});
    if($('#view-streams')?.classList.contains('active'))loadStreams();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  window.loadStreams=loadStreams;
  if(!window.__redSentinelChatLoader){window.__redSentinelChatLoader=true;const load=()=>{if(document.querySelector('script[data-rs-chat]'))return;const s=document.createElement('script');s.src='./chat.js?v=20260911-2';s.dataset.rsChat='1';document.head.appendChild(s);const c=document.createElement('link');c.rel='stylesheet';c.href='./chat.css?v=20260911-2';document.head.appendChild(c)};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load,{once:true});else load()}
})();
