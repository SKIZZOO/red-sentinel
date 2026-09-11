(()=>{
  const apply=()=>{
    const active=document.getElementById('view-server')?.classList.contains('active');
    document.body.classList.toggle('rs-server-fullscreen',!!active);
  };
  apply();
  document.addEventListener('click',e=>{ if(e.target.closest('.nav,[data-view="control"],[data-view="server"]')) setTimeout(apply,0); });
  new MutationObserver(apply).observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});
})();
