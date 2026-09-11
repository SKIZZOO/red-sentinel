(()=>{
  const ROUTES={overview:'/',logs:'/logs',chat:'/chat',members:'/members',moderation:'/moderation',announce:'/announce',streams:'/streams',social:'/social',routing:'/routing',settings:'/settings',control:'/control'};
  const originalNavigate=window.navigate;
  const routeFor=v=>ROUTES[v]||ROUTES.overview;
  const viewFor=path=>{const clean=(path||'/').replace(/\/+$/,'')||'/';return Object.keys(ROUTES).find(k=>ROUTES[k]===clean)||'overview'};
  const navigate=(view,{replace=false}={})=>{const path=routeFor(view);if(location.pathname!==path){history[replace?'replaceState':'pushState']({sentinelView:view},'',path)}originalNavigate?.(view)};
  window.navigate=(view)=>navigate(view);
  window.addEventListener('popstate',()=>navigate(viewFor(location.pathname),{replace:true}));
  document.addEventListener('click',e=>{const b=e.target.closest('.nav[data-view]');if(!b)return;const view=b.dataset.view;if(ROUTES[view])requestAnimationFrame(()=>{const path=routeFor(view);if(location.pathname!==path)history.pushState({sentinelView:view},'',path)})});
  const bootRoute=()=>{const view=viewFor(location.pathname);const path=routeFor(view);if(location.pathname!==path)history.replaceState({sentinelView:view},'',path);originalNavigate?.(view)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(bootRoute,120),{once:true});else setTimeout(bootRoute,120);
})();
