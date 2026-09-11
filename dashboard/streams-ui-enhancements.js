(()=>{
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icons={
    twitch:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 3h17v12l-5 5h-4l-3 3v-3H4z"/><path fill="rgba(5,5,10,.92)" d="M9 8h2v5H9zm5 0h2v5h-2z"/></svg>',
    youtube:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21 7.2a2.8 2.8 0 0 0-2-2C17.2 4.7 12 4.7 12 4.7s-5.2 0-7 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2.5 12 29 29 0 0 0 3 16.8a2.8 2.8 0 0 0 2 2c1.8.5 7 .5 7 .5s5.2 0 7-.5a2.8 2.8 0 0 0 2-2 29 29 0 0 0 .5-4.8 29 29 0 0 0-.5-4.8Z"/><path fill="rgba(5,5,10,.92)" d="m10 9 5 3-5 3z"/></svg>',
    kick:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 4h6v5l4-5h6l-6 8 6 8h-6l-4-5v5H4z"/></svg>',
    x:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M5 4h4.7l3.2 4.5L16.7 4H20l-5.5 6.3L21 20h-4.7l-3.7-5.2L8.1 20H5l5.7-6.6z"/></svg>'
  };
  const names={twitch:'Twitch',youtube:'YouTube',kick:'Kick',x:'X'};
  const api=(path,opts={})=>{const h={'Content-Type':'application/json'};const t=localStorage.getItem('rs_token')||'';if(t)h.Authorization=`Bearer ${t}`;return fetch((localStorage.getItem('rs_api')||location.origin).replace(/\/$/,'')+path,{...opts,headers:{...h,...(opts.headers||{})},cache:'no-store'}).then(async r=>{if(!r.ok)throw new Error((await r.text())||`${r.status} ${r.statusText}`);return r.json()})};
  const gid=()=>String(window.rsState?.guild||'');
  const icon=p=>icons[p]||'<span>◎</span>';
  const injectPlatforms=()=>{
    const hero=document.querySelector('#view-streams .stream-hero'); if(!hero||hero.querySelector('.stream-platforms'))return;
    const node=document.createElement('div');node.className='stream-platforms';
    node.innerHTML=['twitch','youtube','kick','x'].map(p=>`<div class="stream-platform-card ${p}"><div class="stream-platform-mark">${icon(p)}</div><div><b>${names[p]}</b><span>${p==='x'?'Posts → Discord':'Live → Discord'}</span></div></div>`).join('');
    hero.insertAdjacentElement('afterend',node);
  };
  const statusData=x=>{
    const live=x.live===true||x.status==='live';
    const unknown=x.status==='unknown' || (!!x.last_error && x.live==null);
    const last=x.last_alert_at||x.last_alert||0;
    const sent=x.last_alert_ok===true || !!last;
    let label=live?'LIVE':unknown?'CHECK FAILED':'OFFLINE';
    let cls=live?'live':unknown?'unknown':'offline';
    let detail=unknown?(x.last_error||'Platform status could not be determined.'):(sent?`Last alert: ${new Date(last*1000).toLocaleString([], {month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'})}`:'No alert sent yet');
    if(x.last_alert_ok===false) detail=`Alert failed: ${x.last_alert_error||x.last_error||'unknown error'}`;
    return {live,unknown,cls,label,detail};
  };
  const decorate=()=>{
    const box=document.querySelector('#streamList'); if(!box)return;
    box.querySelectorAll('.stream-item').forEach((item,i)=>{
      if(item.dataset.uiEnhanced)return; item.dataset.uiEnhanced='1';
      const text=item.querySelector('.stream-main'); const actions=item.querySelector('.stream-actions');
      const platform=(item.querySelector('.stream-brand')?.className||'').split(/\s+/).find(x=>['twitch','youtube','kick'].includes(x))||'';
      const probe=document.createElement('button');probe.type='button';probe.className='ghost stream-check-now';probe.textContent='Check now';
      const result=document.createElement('div');result.className='stream-check-result';result.textContent='';
      if(text)text.appendChild(result);
      if(actions){actions.insertBefore(probe,actions.firstChild);probe.addEventListener('click',()=>checkItem(item,probe,result));}
      const original=item.querySelector('.live-pill'); if(original){original.classList.add('stream-status-pill');}
    });
  };
  async function checkItem(item,button,result){
    const id=[...item.querySelectorAll('button')].find(b=>b.dataset.id)?.dataset.id || item.querySelector('.stream-toggle')?.dataset.id || item.querySelector('.stream-delete')?.dataset.id;
    if(!id||!gid())return toast('Livestream source ID unavailable.');
    button.disabled=true;button.textContent='Checking…';result.textContent='Contacting provider…';
    try{
      const r=await api(`/api/guilds/${gid()}/streams`,{method:'POST',body:JSON.stringify({action:'check',id})});
      const source=(r.sources||[]).find(x=>String(x.id)===String(id))||r.source; const s=statusData(source||{});
      const pill=item.querySelector('.stream-status-pill'); if(pill){pill.className=`live-pill stream-status-pill ${s.live?'is-live':''}`;pill.textContent=s.live?'● LIVE':s.unknown?'● UNKNOWN':'● OFFLINE';}
      result.innerHTML=`<span class="check-state ${s.cls}">${esc(s.label)}</span><span>${esc(s.detail)}</span>`;
      button.textContent='Check again';
      if(s.live)toast('LIVE — provider confirms the stream is live.'); else if(s.unknown)toast('Could not determine the live status.'); else toast('OFFLINE — provider reports no live stream.');
      return r;
    }catch(e){result.textContent=`Check failed: ${e.message}`;button.textContent='Try again';toast('Live check failed: '+e.message)}finally{button.disabled=false;}
  }
  const wrap=()=>{
    const original=window.loadStreams;
    if(typeof original!=='function'||window.__streamUiWrapped)return;
    window.__streamUiWrapped=true;
    window.loadStreams=async()=>{const r=await original();injectPlatforms();decorate();return r};
    injectPlatforms();decorate();
  };
  const toast=t=>window.toast?window.toast(t):console.log(t);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(wrap,0),{once:true});else setTimeout(wrap,0);
  setTimeout(wrap,250);setTimeout(wrap,1000);setTimeout(wrap,2500);
})();
