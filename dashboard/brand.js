(()=>{
  const SRC='./assets/red-sentinel.svg?v=20260911-1';
  const installHead=()=>{
    if(!document.querySelector('link[rel="icon"]')){const l=document.createElement('link');l.rel='icon';l.type='image/svg+xml';l.href=SRC;document.head.appendChild(l)}
    if(!document.querySelector('link[rel="apple-touch-icon"]')){const l=document.createElement('link');l.rel='apple-touch-icon';l.href=SRC;document.head.appendChild(l)}
    let meta=document.querySelector('meta[name="theme-color"]');
    if(!meta){meta=document.createElement('meta');meta.name='theme-color';document.head.appendChild(meta)}
    meta.content='#070812';
  };
  const paint=()=>{
    const brand=document.querySelector('.brand'); if(!brand)return;
    const mark=brand.querySelector('.brand-mark');
    if(mark){
      mark.classList.add('brand-logo-wrap');
      mark.innerHTML='<img class="brand-logo" src="'+SRC+'" alt="Red Sentinel">';
      mark.setAttribute('aria-label','Red Sentinel');
    }
    document.title='Red Sentinel — Command Center';
  };
  installHead(); paint();
  new MutationObserver(paint).observe(document.body,{childList:true,subtree:true});
})();
