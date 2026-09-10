(()=>{
  let wanted='', guardTimer=null;
  const getGuild=()=>String(window.rsState?.guild||'');
  const key=()=>{const g=getGuild();return g?`red-sentinel-chat-channel:${g}`:''};
  const save=cid=>{try{const k=key();if(k&&cid)sessionStorage.setItem(k,String(cid))}catch{}};
  const active=()=>document.querySelector('.chat-channel.active')?.dataset?.cid||'';
  const syncComposer=()=>{
    const room=document.querySelector('#chatRoomName');
    const compose=document.querySelector('#chatCompose');
    const hint=document.querySelector('.chat-compose-foot span:nth-of-type(2)');
    const raw=room?.textContent?.trim()||'';
    if(!raw||raw==='Select a channel'||raw==='# channel')return;
    const name=raw.replace(/^#\s*/,'').trim();
    if(!name)return;
    if(compose)compose.placeholder=`Message #${name}…`;
    if(hint)hint.textContent=`Scrii în #${name} · Enter pentru trimitere · Shift+Enter pentru rând nou`;
  };
  const clickWanted=()=>{
    if(!wanted||!document.querySelector('#chatView')){syncComposer();return}
    const current=String(active()||'');
    if(current===String(wanted)){syncComposer();return}
    const btn=[...document.querySelectorAll('.chat-channel')].find(b=>String(b.dataset.cid)===String(wanted));
    if(btn)btn.click();
    syncComposer();
  };
  const arm=cid=>{
    wanted=String(cid||'');
    save(wanted);
    clearTimeout(guardTimer);
    [0,80,220,500,900,1500,2200].forEach(ms=>setTimeout(()=>{clickWanted();syncComposer()},ms));
  };
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('.chat-channel');
    if(!btn)return;
    arm(btn.dataset.cid);
  },true);
  document.addEventListener('change',e=>{
    if(e.target?.id!=='guildSelect')return;
    wanted='';
    setTimeout(syncComposer,500);
  },true);
  const watch=()=>{
    const box=document.querySelector('#chatChannelList');
    if(!box)return;
    new MutationObserver(()=>{if(wanted&&String(window.rsState?.guild||''))setTimeout(clickWanted,0);syncComposer()}).observe(box,{childList:true,subtree:true});
    const room=document.querySelector('#chatRoomName');
    if(room)new MutationObserver(syncComposer).observe(room,{childList:true,characterData:true,subtree:true});
    syncComposer();
  };
  setTimeout(watch,300);
  setTimeout(()=>{
    try{const k=key();const saved=k&&sessionStorage.getItem(k);if(saved)wanted=String(saved)}catch{}
    syncComposer();
  },500);
  setTimeout(syncComposer,1000);
})();
