(()=>{
  const $=s=>document.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api=(path,opts={})=>{const h={'Content-Type':'application/json'},t=localStorage.getItem('rs_token')||'';if(t)h.Authorization=`Bearer ${t}`;return fetch((localStorage.getItem('rs_api')||location.origin).replace(/\/$/,'')+path,{...opts,headers:{...h,...(opts.headers||{})},cache:'no-store'}).then(async r=>{if(!r.ok)throw new Error((await r.text())||`${r.status} ${r.statusText}`);return r.json()})};
  const gid=()=>String(window.rsState?.guild||'');
  const toast=t=>window.toast?window.toast(t):console.log(t);
  const platforms={
    twitch:{n:'Twitch',c:'twitch',icon:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M4 3h17v12l-5 5h-4l-3 3v-3H4z"/><path fill="rgba(5,5,10,.9)" d="M9 8h2v5H9zm5 0h2v5h-2z"/></svg>'},
    youtube:{n:'YouTube',c:'youtube',icon:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M21 7.2a2.8 2.8 0 0 0-2-2C17.2 4.7 12 4.7 12 4.7s-5.2 0-7 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2.5 12 29 29 0 0 0 3 16.8a2.8 2.8 0 0 0 2 2c1.8.5 7 .5 7 .5s5.2 0 7-.5a2.8 2.8 0 0 0 2-2 29 29 0 0 0 .5-4.8 29 29 0 0 0-.5-4.8Z"/><path fill="rgba(5,5,10,.9)" d="m10 9 5 3-5 3z"/></svg>'},
    kick:{n:'Kick',c:'kick',icon:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M4 4h6v5l4-5h6l-6 8 6 8h-6l-4-5v5H4z"/></svg>'},
    x:{n:'X',c:'x',icon:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M5 4h4.7l3.2 4.5L16.7 4H20l-5.5 6.3L21 20h-4.7l-3.7-5.2L8.1 20H5l5.7-6.6z"/></svg>'}
  };
  function injectPlatformRail(){
    const hero=$('#view-streams .stream-hero');if(!hero||hero.nextElementSibling?.classList.contains('stream-platform-rail'))return;
    const rail=document.createElement('div');rail.className='stream-platform-rail';
    rail.innerHTML=Object.keys(platforms).map(k=>{const p=platforms[k];return `<div class="stream-platform-tile ${p.c}"><span class="stream-platform-tile__icon">${p.icon}</span><span><b>${p.n}</b><small>${k==='x'?'Social signals':'Live streaming'}</small></span><i>●</i></div>`}).join('');hero.insertAdjacentElement('afterend',rail);
  }
  function status(x){if(x?.live===true||x?.status==='live')return ['LIVE','live'];if(x?.last_error)return ['CHECK ERROR','error'];return [x?.enabled===false?'PAUSED':'MONITORING',''];}
  function alertInfo(x){const ts=Number(x?.last_alert_at||x?.last_alert||0);if(x?.last_alert_ok===false)return `Alert failed${x.last_alert_error?': '+x.last_alert_error:''}`;return ts?`Alert sent · ${new Date(ts*1000).toLocaleString([],{month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'})}`:'No alert sent yet';}
  async function loadStreams(){
    if(!gid())return;
    try{
      const [data,g]=await Promise.all([api(`/api/guilds/${gid()}/streams`),api(`/api/guilds/${gid()}`)]);
      const channels=(g.channels||[]).filter(c=>c.type==='text');const sel=$('#streamChannel');if(sel)sel.innerHTML=channels.map(c=>`<option value="${String(c.id)}"># ${esc(c.name)}</option>`).join('');
      const s=data.sources||[],st=data.settings||{};
      if($('#streamDefaultTitle'))$('#streamDefaultTitle').value=st.title||'🔴 {name} is LIVE!';if($('#streamDefaultColor'))$('#streamDefaultColor').value=st.color||'9146FF';if($('#streamDefaultMessage'))$('#streamDefaultMessage').value=st.message||'{name} just went live on {platform}. Come hang out!';if($('#streamDedupe'))$('#streamDedupe').checked=st.dedupe!==false;
      render(s);injectPlatformRail();if($('#streamCount'))$('#streamCount').textContent=`${s.length} source${s.length===1?'':'s'}`;
    }catch(e){toast('Livestreams failed: '+e.message)}
  }
  function render(items){
    const box=$('#streamList');if(!box)return;
    if(!items.length){box.innerHTML='<div class="stream-empty"><div class="empty-icon">◉</div><b>No livestream sources yet</b><span>Add a Twitch, YouTube or Kick channel and choose a Discord destination.</span></div>';return;}
    box.innerHTML=items.map(x=>{const p=String(x.platform||'twitch').toLowerCase(),d=platforms[p]||platforms.twitch,[label,cls]=status(x);return `<article class="stream-item ${x.enabled?'':'disabled'}" data-stream-id="${esc(x.id)}"><div class="stream-brand ${d.c}">${d.icon}</div><div class="stream-main"><div class="stream-name"><b>${esc(x.name)}</b><span class="live-pill ${cls==='live'?'is-live':''} ${cls==='error'?'is-error':''}">● ${label}</span></div><div class="stream-platform-name">${esc(d.n.toUpperCase())} · ${x.last_checked?'Last check '+new Date(Number(x.last_checked)*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'Never checked'}</div><a class="stream-url" href="${esc(x.url)}" target="_blank" rel="noreferrer">${esc(x.url)}</a><small>→ Discord channel ${esc(x.channel_id)}</small><div class="stream-alert-state">${esc(alertInfo(x))}</div></div><div class="stream-actions"><button type="button" class="ghost stream-check" data-id="${esc(x.id)}">Check now</button><button type="button" class="ghost stream-toggle" data-id="${esc(x.id)}">${x.enabled?'Pause':'Resume'}</button><button type="button" class="danger stream-delete" data-id="${esc(x.id)}">Remove</button></div></article>`}).join('');
    box.querySelectorAll('.stream-check').forEach(b=>b.onclick=()=>check(b));box.querySelectorAll('.stream-toggle').forEach(b=>b.onclick=()=>action('toggle',b.dataset.id));box.querySelectorAll('.stream-delete').forEach(b=>b.onclick=()=>action('delete',b.dataset.id));
  }
  async function check(b){const id=b.dataset.id;if(!id||!gid())return;b.disabled=true;b.textContent='Checking…';const row=b.closest('.stream-item'),info=row?.querySelector('.stream-alert-state');if(info)info.textContent='Checking provider…';try{const r=await api(`/api/guilds/${gid()}/streams`,{method:'POST',body:JSON.stringify({action:'check',id})});const x=(r.sources||[]).find(s=>String(s.id)===String(id));if(x){const [label,cls]=status(x),pill=row.querySelector('.live-pill');if(pill){pill.textContent='● '+label;pill.className=`live-pill ${cls==='live'?'is-live':''} ${cls==='error'?'is-error':''}`}if(info)info.textContent=`${label} · ${alertInfo(x)}`;toast(label==='LIVE'?'LIVE — detected now.':label==='OFFLINE'?'OFFLINE — not live.':'Could not determine provider status.')}b.textContent='Check again';}catch(e){if(info)info.textContent='Check failed · '+e.message;b.textContent='Try again';toast('Live check failed: '+e.message)}finally{b.disabled=false}}
  async function action(a,id){try{const r=await api(`/api/guilds/${gid()}/streams`,{method:'POST',body:JSON.stringify({action:a,id})});render(r.sources||[]);injectPlatformRail();toast(a==='delete'?'Livestream removed':a==='toggle'?'Livestream updated':'Livestream checked')}catch(e){toast('Livestream action failed: '+e.message)}}
  async function add(){const url=$('#streamUrl')?.value.trim()||'';if(!url)return toast('Add a livestream URL first.');try{const r=await api(`/api/guilds/${gid()}/streams`,{method:'POST',body:JSON.stringify({action:'add',platform:$('#streamPlatform')?.value,name:$('#streamName')?.value,url,channel_id:$('#streamChannel')?.value,title:$('#streamTitle')?.value,image:$('#streamImage')?.value,mention_everyone:$('#streamMention')?.checked})});render(r.sources||[]);injectPlatformRail();$('#streamUrl').value='';$('#streamName').value='';$('#streamTitle').value='';$('#streamImage').value='';$('#streamMention').checked=false;toast('Livestream source added. Monitoring is active.')}catch(e){toast('Could not add livestream: '+e.message)}}
  async function saveSettings(){try{await api(`/api/guilds/${gid()}/streams/settings`,{method:'PUT',body:JSON.stringify({title:$('#streamDefaultTitle')?.value,message:$('#streamDefaultMessage')?.value,color:$('#streamDefaultColor')?.value,dedupe:$('#streamDedupe')?.checked})});toast('Livestream notification settings saved.')}catch(e){toast('Settings failed: '+e.message)}}
  function bind(){if($('#addStream')?.dataset.streamBound!=='1'){$('#addStream').dataset.streamBound='1';$('#addStream').onclick=add}if($('#saveStreamSettings')?.dataset.streamBound!=='1'){$('#saveStreamSettings').dataset.streamBound='1';$('#saveStreamSettings').onclick=saveSettings}injectPlatformRail();loadStreams()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
  const old=window.loadStreams;if(old!==loadStreams){window.loadStreams=loadStreams;}
  new MutationObserver(()=>{if($('#view-streams')?.classList.contains('active')){injectPlatformRail();if(!$('#streamList')?.dataset.streamBound)bind()}}).observe(document.body,{childList:true,subtree:true});
})();
