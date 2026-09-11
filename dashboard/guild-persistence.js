(()=>{
  const KEY='red-sentinel:selected-guild';
  const read=()=>{try{return localStorage.getItem(KEY)||''}catch{return''}};
  const write=v=>{try{if(v)localStorage.setItem(KEY,String(v))}catch{}};
  let restoring=false;
  const select=()=>document.querySelector('#guildSelect');
  const restore=()=>{
    const s=select(), saved=read();
    if(!s||!saved||!s.options.length||restoring)return false;
    const exists=[...s.options].some(o=>String(o.value)===String(saved));
    if(!exists)return false;
    if(String(s.value)!==String(saved)){
      restoring=true;
      s.value=saved;
      s.dispatchEvent(new Event('change',{bubbles:true}));
      setTimeout(()=>{restoring=false},0);
    }
    return true;
  };
  const bind=()=>{
    const s=select();
    if(!s||s.dataset.guildPersistBound)return;
    s.dataset.guildPersistBound='1';
    s.addEventListener('change',()=>{if(!restoring&&s.value)write(s.value)});
  };
  const tick=()=>{bind();restore()};
  tick();
  const obs=new MutationObserver(tick);
  obs.observe(document.body,{childList:true,subtree:true});
  [50,200,500,1000,2000,4000].forEach(ms=>setTimeout(tick,ms));
  addEventListener('pageshow',tick);
  window.addEventListener('storage',e=>{if(e.key===KEY)tick()});
})();
