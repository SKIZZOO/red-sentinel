(() => {
  const $ = s => document.querySelector(s);
  const api = window.api || ((path, opts={}) => { const h={'Content-Type':'application/json'}; const t=localStorage.getItem('rs_token')||''; if(t) h.Authorization=`Bearer ${t}`; return fetch((localStorage.getItem('rs_api')||location.origin).replace(/\/$/,'')+path,{...opts,headers:h,cache:'no-store'}).then(async r=>{if(!r.ok)throw new Error((await r.text())||`${r.status} ${r.statusText}`);return r.json()}) });
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const toast = t => window.toast ? window.toast(t) : (()=>{const e=$('#toast');if(e){e.textContent=t;e.classList.add('show');setTimeout(()=>e.classList.remove('show'),3000)}})();
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
    box.innerHTML=items.map(x=>`<div class="stream-item ${x.enabled?'':'disabled'}"><div class="stream-icon ${esc(x.platform)}">${x.platform==='twitch'?'TW':x.platform==='youtube'?'YT':'KI'}</div><div class="stream-main"><div class="stream-name"><b>${esc(x.name)}</b><span class="live-pill ${x.live?'is-live':''}">${x.live?'● LIVE':x.enabled?'● MONITORING':'○ PAUSED'}</span></div><small>${esc(x.url)}</small><small>→ Discord channel ${esc(x.channel_id)}</small></div><div class="stream-actions"><button class="ghost stream-toggle" data-id="${esc(x.id)}">${x.enabled?'Pause':'Resume'}</button><button class="danger stream-delete" data-id="${esc(x.id)}">Remove</button></div></div>`).join('');
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
})();
