(()=>{
  const KEY='rs_selected_guild';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let picker=null, select=null, observer=null;
  const saved=()=>{try{return localStorage.getItem(KEY)||localStorage.getItem('red-sentinel:selected-guild')||''}catch{return''}};
  const save=v=>{try{if(v)localStorage.setItem(KEY,String(v))}catch{}};
  const ensure=()=>{
    select=document.querySelector('#guildSelect');
    if(!select)return;
    if(select.dataset.premiumGuildBound!=='1'){
      select.dataset.premiumGuildBound='1';
      select.addEventListener('change',()=>{save(select.value);render()});
    }
    if(!picker){
      picker=document.createElement('div');
      picker.className='guild-picker';
      picker.innerHTML=`<button type="button" class="guild-picker__trigger" aria-expanded="false"><span class="guild-picker__orb">RS</span><span class="guild-picker__copy"><span class="guild-picker__name">Select server</span><span class="guild-picker__meta">Discord server</span></span><span class="guild-picker__chev">⌄</span></button><div class="guild-picker__menu"><label class="guild-picker__search"><span>⌕</span><input type="search" placeholder="Search servers…" autocomplete="off"></label><div class="guild-picker__list"></div></div>`;
      select.parentNode.insertBefore(picker,select); select.style.display='none';
      const trigger=picker.querySelector('.guild-picker__trigger');
      trigger.addEventListener('click',e=>{e.preventDefault();const open=picker.classList.toggle('open');trigger.setAttribute('aria-expanded',String(open));if(open){picker.querySelector('input').focus();renderList()}});
      picker.addEventListener('click',e=>{
        const item=e.target.closest('[data-guild-id]'); if(!item)return;
        const id=item.dataset.guildId; select.value=id; save(id); picker.classList.remove('open'); trigger.setAttribute('aria-expanded','false'); select.dispatchEvent(new Event('change',{bubbles:true}));
      });
      picker.querySelector('input').addEventListener('input',renderList);
      document.addEventListener('click',e=>{if(picker&&!picker.contains(e.target)){picker.classList.remove('open');trigger.setAttribute('aria-expanded','false')}});
      window.addEventListener('storage',e=>{if(e.key===KEY||e.key==='red-sentinel:selected-guild'){restore();render()}});
    }
    restore(); render();
    if(!observer){observer=new MutationObserver(()=>{restore();render()});observer.observe(select,{childList:true,subtree:true,attributes:true})}
  };
  const restore=()=>{
    if(!select)return;
    const target=saved();
    if(target && [...select.options].some(o=>String(o.value)===String(target)) && select.value!==target){select.value=target;select.dispatchEvent(new Event('change',{bubbles:true}))}
  };
  const selected=()=>select?.selectedOptions?.[0];
  const render=()=>{
    if(!picker||!select)return;
    const o=selected();
    const name=o?.textContent?.split(' · ')[0]?.trim()||'Select server';
    const meta=o?`Server • ${String(o.value).slice(-8)}`:'Discord server';
    picker.querySelector('.guild-picker__name').textContent=name;
    picker.querySelector('.guild-picker__meta').textContent=meta;
    renderList();
  };
  const renderList=()=>{
    if(!picker||!select)return;
    const q=(picker.querySelector('input')?.value||'').toLowerCase().trim();
    const current=String(select.value||'');
    const list=picker.querySelector('.guild-picker__list');
    const opts=[...select.options].filter(o=>!q||o.textContent.toLowerCase().includes(q));
    list.innerHTML=opts.length?opts.map(o=>{const name=o.textContent.split(' · ')[0].trim();const active=String(o.value)===current;return `<button type="button" class="guild-picker__item ${active?'is-active':''}" data-guild-id="${esc(o.value)}"><span class="guild-picker__item-orb">RS</span><span class="guild-picker__item-copy"><span class="guild-picker__item-name">${esc(name)}</span><span class="guild-picker__item-meta">Discord server</span></span><span class="guild-picker__check">✓</span></button>`}).join(''):`<div class="guild-picker__empty">No servers found</div>`;
  };
  const boot=()=>ensure();
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  setTimeout(boot,50);setTimeout(boot,200);setTimeout(boot,500);setTimeout(boot,1000);setTimeout(boot,2000);
})();
