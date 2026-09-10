(()=>{
  const $=s=>document.querySelector(s);
  let cacheGuild='',roles=new Map(),busy=false;
  async function loadRoles(){
    const st=window.rsState,gid=String(st?.guild||'');
    if(!gid||gid===cacheGuild||busy)return;
    busy=true;
    try{
      const h={};if(st?.token)h.Authorization=`Bearer ${st.token}`;
      const r=await fetch((st?.api||location.origin).replace(/\/$/,'')+`/api/guilds/${gid}/roles?_t=${Date.now()}`,{headers:h,cache:'no-store'});
      if(!r.ok)throw new Error('roles '+r.status);
      const data=await r.json();roles=new Map((data.roles||[]).map(x=>[String(x.name),Number(x.color||0)]));cacheGuild=gid;
    }catch(e){console.debug('role colors',e)}finally{busy=false}
  }
  function paint(){
    document.querySelectorAll('.chat-role').forEach(el=>{
      const name=el.querySelector(':scope > span')?.textContent?.trim();if(!name)return;
      const value=roles.get(name);if(!value)return;
      const hex='#'+value.toString(16).padStart(6,'0');
      el.style.setProperty('--role-color',hex);el.style.setProperty('--role-bg',hex+'22');el.style.setProperty('--role-border',hex+'70');el.classList.add('discord-role-colored');
    });
  }
  async function sync(){await loadRoles();paint()}
  const mo=new MutationObserver(()=>paint());
  function start(){const root=$('#chatMessages')||document.body;mo.observe(root,{subtree:true,childList:true});sync();setInterval(sync,15000)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.refreshDiscordRoleColors=sync;
})();
