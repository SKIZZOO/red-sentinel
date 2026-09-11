(()=>{
  const dedupe=()=>{
    const items=[...document.querySelectorAll('.sidebar .nav[data-view="chat"]')];
    if(items.length<=1)return;
    items.slice(1).forEach(x=>x.remove());
    const keep=document.querySelector('.sidebar .nav[data-view="chat"]');
    if(keep){keep.classList.add('nav');keep.innerHTML='<span class="nav-icon">▣</span><span>Server Chat</span>';}
  };
  dedupe();
  new MutationObserver(dedupe).observe(document.querySelector('.sidebar nav')||document.body,{childList:true,subtree:true});
  window.setTimeout(dedupe,100);
  window.setTimeout(dedupe,500);
  window.setTimeout(dedupe,1500);
})();
