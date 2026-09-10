(()=>{
  let wanted='', guardTimer=null;
  const getGuild=()=>String(window.rsState?.guild||'');
  const key=()=>{const g=getGuild();return g?`red-sentinel-chat-channel:${g}`:''};
  const save=cid=>{try{const k=key();if(k&&cid)sessionStorage.setItem(k,String(cid))}catch{}};
  const active=()=>document.querySelector('.chat-channel.active')?.dataset?.cid||'';
  const clickWanted=()=>{
    if(!wanted||!document.querySelector('#chatView'))return;
    const current=String(active()||'');
    if(current===String(wanted))return;
    const btn=[...document.querySelectorAll('.chat-channel')].find(b=>String(b.dataset.cid)===String(wanted));
    if(btn){btn.click();}
  };
  const arm=cid=>{
    wanted=String(cid||'');
    save(wanted);
    clearTimeout(guardTimer);
    [0,80,220,500,900,1500,2200].forEach(ms=>setTimeout(clickWanted,ms));
  };
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('.chat-channel');
    if(!btn)return;
    arm(btn.dataset.cid);
  },true);
  document.addEventListener('change',e=>{
    if(e.target?.id!=='guildSelect')return;
    wanted='';
  },true);
  const watch=()=>{
    const box=document.querySelector('#chatChannelList');
    if(!box)return;
    new MutationObserver(()=>{if(wanted&&String(window.rsState?.guild||''))setTimeout(clickWanted,0)}).observe(box,{childList:true,subtree:true});
  };
  setTimeout(watch,300);
  setTimeout(()=>{
    try{const k=key();const saved=k&&sessionStorage.getItem(k);if(saved)wanted=String(saved)}catch{}
  },500);
})();
