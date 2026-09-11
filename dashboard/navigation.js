(()=>{
  const ROUTES={
    overview:'/',
    logs:'/logs',
    chat:'/chat',
    members:'/members',
    moderation:'/moderation',
    announce:'/announce',
    streams:'/streams',
    social:'/social',
    routing:'/routing',
    settings:'/settings',
    control:'/control'
  };
  const routeFor=v=>ROUTES[v]||ROUTES.overview;
  const viewFor=path=>{
    const clean=(path||'/').replace(/\/+$/,'')||'/';
    return Object.keys(ROUTES).find(k=>ROUTES[k]===clean)||'overview';
  };
  const navigate=(view,{replace=false}={})=>{
    const path=routeFor(view);
    if(location.pathname!==path){
      const method=replace?'replaceState':'pushState';
      history[method]({sentinelView:view},'',path);
    }
    window.navigate?.(view);
  };
  const apply=({replace=false}={})=>navigate(viewFor(location.pathname),{replace});
  window.addEventListener('popstate',()=>apply());
  document.addEventListener('click',e=>{
    const b=e.target.closest('.nav[data-view]');
    if(!b)return;
    const view=b.dataset.view;
    if(!ROUTES[view])return;
    requestAnimationFrame(()=>{
      if(location.pathname!==routeFor(view))history.pushState({sentinelView:view},'',routeFor(view));
    });
  });
  const oldNavigate=window.navigate;
  window.navigate=(view)=>navigate(view);
  const bootRoute=()=>{
    const view=viewFor(location.pathname);
    if(location.pathname!==routeFor(view))history.replaceState({sentinelView:view},'',routeFor(view));
    oldNavigate?.(view);
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(bootRoute,120),{once:true});
  else setTimeout(bootRoute,120);
})();
