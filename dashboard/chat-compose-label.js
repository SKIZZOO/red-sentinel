(()=>{
  const sync=()=>{
    const name=document.querySelector('#chatRoomName')?.textContent?.trim();
    if(!name||name==='Select a channel'||name==='# channel')return;
    const channel=name.replace(/^#\s*/,'# ');
    const compose=document.querySelector('#chatCompose');
    if(compose)compose.placeholder=`Message in ${channel}…`;
    const foot=document.querySelector('.chat-compose-foot');
    const hint=foot?.querySelector('span:nth-of-type(2)');
    if(hint)hint.textContent=`Scrii în ${channel} · Enter pentru trimitere · Shift+Enter pentru rând nou`;
  };
  const observer=new MutationObserver(sync);
  const start=()=>{
    const head=document.querySelector('#chatRoomName');
    if(head)observer.observe(head,{childList:true,characterData:true,subtree:true});
    sync();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  setTimeout(start,500);
  setTimeout(start,1500);
})();
