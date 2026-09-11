(()=>{
  const reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(!reduce){
    const glow=document.createElement('div');glow.className='cursor-glow';document.body.appendChild(glow);
    let tx=innerWidth/2,ty=innerHeight/2,x=tx,y=ty;addEventListener('pointermove',e=>{tx=e.clientX;ty=e.clientY});
    const tick=()=>{x+=(tx-x)*.14;y+=(ty-y)*.14;glow.style.left=`${x}px`;glow.style.top=`${y}px`;requestAnimationFrame(tick)};tick();
    const bindMagnetic=()=>{document.querySelectorAll('.primary,.ghost,.icon-btn,.avatar,.nav').forEach(el=>{if(el.dataset.kinetic)return;el.dataset.kinetic='1';el.classList.add('magnetic');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect(),ox=e.clientX-(r.left+r.width/2),oy=e.clientY-(r.top+r.height/2);el.style.transform=`translate(${ox*.08}px,${oy*.08}px)`});el.addEventListener('pointerleave',()=>el.style.transform='')})};
    const bindTilt=()=>{document.querySelectorAll('.stat,.social-card,.hero').forEach(el=>{if(el.dataset.tiltBound)return;el.dataset.tiltBound='1';el.classList.add('tilt');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect(),px=(e.clientX-r.left)/r.width-.5,py=(e.clientY-r.top)/r.height-.5;el.style.transform=`perspective(900px) rotateX(${(-py*2.2).toFixed(2)}deg) rotateY(${(px*2.8).toFixed(2)}deg) translateY(-2px)`});el.addEventListener('pointerleave',()=>el.style.transform='')})};
    const bindRipple=()=>{document.querySelectorAll('button').forEach(btn=>{if(btn.dataset.ripple)return;btn.dataset.ripple='1';btn.style.position='relative';btn.style.overflow='hidden';btn.addEventListener('pointerdown',e=>{const r=btn.getBoundingClientRect(),size=Math.max(r.width,r.height)*1.4,dot=document.createElement('i');dot.style.cssText=`position:absolute;width:${size}px;height:${size}px;left:${e.clientX-r.left-size/2}px;top:${e.clientY-r.top-size/2}px;border-radius:50%;background:rgba(255,255,255,.16);transform:scale(0);pointer-events:none;animation:rs-ripple .6s ease-out forwards`;btn.appendChild(dot);setTimeout(()=>dot.remove(),650)})})};
    const bindAll=()=>{bindMagnetic();bindTilt();bindRipple()};const style=document.createElement('style');style.textContent='@keyframes rs-ripple{to{transform:scale(1);opacity:0}}';document.head.appendChild(style);bindAll();new MutationObserver(bindAll).observe(document.body,{childList:true,subtree:true});
  }
  const load=(kind,tag,src)=>{if(document.querySelector(`[data-${kind}]`))return;const e=document.createElement(tag);e.src=src;e.dataset[kind]='1';e.async=false;document.body.appendChild(e)};
  const css=(kind,src)=>{if(document.querySelector(`[data-${kind}]`))return;const e=document.createElement('link');e.rel='stylesheet';e.href=src;e.dataset[kind]='1';document.head.appendChild(e)};
  css('chat-css','./chat.css?v=20260911-7');load('chat-js','script','./chat.js?v=20260911-7');load('chat-nav-dedupe-js','script','./chat-nav-dedupe.js?v=20260911-1');
  css('logs-css','./logs.css?v=20260911-7');load('confirm-js','script','./confirm-actions.js?v=20260911-3');load('logs-js','script','./logs-enhancements.js?v=20260911-7');
  css('moderation-css','./moderation.css?v=20260911-2');load('moderation-js','script','./moderation.js?v=20260911-2');
  css('confirm-css','./confirm-actions.css?v=20260911-3');
  css('moderation-polish-css','./moderation-polish.css?v=20260911-1');load('moderation-polish-js','script','./moderation-polish.js?v=20260911-1');
  css('sidebar-polish-css','./sidebar-polish.css?v=20260911-2');
  css('server-polish-css','./server-polish.css?v=20260911-4');load('server-fix-js','script','./server-fix.js?v=20260911-1');load('platform-icons-js','script','./platform-icons.js?v=20260911-1');
})();
