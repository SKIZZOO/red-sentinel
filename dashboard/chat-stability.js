(()=>{
  const stop=()=>{try{window.stopChatLive?.()}catch{}};
  const wrap=(name)=>{
    const original=window[name];
    if(typeof original!=='function'||original.__stabilityWrapped)return;
    const wrapped=async(...args)=>{try{return await original(...args)}finally{stop()}};
    wrapped.__stabilityWrapped=true;
    window[name]=wrapped;
  };
  const arm=()=>{wrap('loadChat');wrap('refreshChat');stop()};
  arm();
  document.addEventListener('click',e=>{
    if(e.target.closest?.('.nav[data-view="chat"]'))setTimeout(stop,200);
  },true);
  document.addEventListener('change',e=>{
    if(e.target?.id==='guildSelect')setTimeout(stop,700);
  },true);
  setTimeout(arm,100);
  setTimeout(arm,500);
})();
