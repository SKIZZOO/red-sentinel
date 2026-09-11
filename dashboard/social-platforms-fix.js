(()=>{
  const icons={
    twitch:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 3h17v12l-5 5h-4l-3 3v-3H4z"/><path fill="#0b0914" d="M9 8h2v5H9zm5 0h2v5h-2z"/></svg>',
    youtube:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21 7.2a2.8 2.8 0 0 0-2-2C17.2 4.7 12 4.7 12 4.7s-5.2 0-7 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2.5 12 29 29 0 0 0 3 16.8a2.8 2.8 0 0 0 2 2c1.8.5 7 .5 7 .5s5.2 0 7-.5a2.8 2.8 0 0 0 2-2 29 29 0 0 0 .5-4.8 29 29 0 0 0-.5-4.8Z"/><path fill="#0b0914" d="m10 9 5 3-5 3z"/></svg>',
    kick:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 4h6v5l4-5h6l-6 8 6 8h-6l-4-5v5H4z"/></svg>',
    x:'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M5 4h4.7l3.2 4.5L16.7 4H20l-5.5 6.3L21 20h-4.7l-3.7-5.2L8.1 20H5l5.7-6.6z"/></svg>'
  };
  const draw=()=>document.querySelectorAll('.social-grid .social-card').forEach(card=>{if(card.querySelector('.social-platform-icon,.platform-card-icon'))return;const p=card.classList.contains('twitch')?'twitch':card.classList.contains('youtube')?'youtube':card.classList.contains('kick')?'kick':card.classList.contains('x')?'x':'';if(!p)return;const el=document.createElement('div');el.className='social-platform-icon';el.innerHTML=icons[p];card.insertBefore(el,card.firstChild)});
  const boot=()=>{draw();setTimeout(draw,150);setTimeout(draw,700);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  new MutationObserver(draw).observe(document.body,{childList:true,subtree:true});
})();
