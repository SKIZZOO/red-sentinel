(()=>{
  const svg={
    twitch:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M4 3h17v12l-5 5h-4l-3 3v-3H4z"/><path fill="#0b0914" d="M9 8h2v5H9zm5 0h2v5h-2z"/></svg>',
    youtube:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M21 7.2a2.8 2.8 0 0 0-2-2C17.2 4.7 12 4.7 12 4.7s-5.2 0-7 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 2.5 12 29 29 0 0 0 3 16.8a2.8 2.8 0 0 0 2 2c1.8.5 7 .5 7 .5s5.2 0 7-.5a2.8 2.8 0 0 0 2-2 29 29 0 0 0 .5-4.8 29 29 0 0 0-.5-4.8Z"/><path fill="#0b0914" d="m10 9 5 3-5 3z"/></svg>',
    kick:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M4 4h6v5l4-5h6l-6 8 6 8h-6l-4-5v5H4z"/></svg>',
    x:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M5 4h4.7l3.2 4.5L16.7 4H20l-5.5 6.3L21 20h-4.7l-3.7-5.2L8.1 20H5l5.7-6.6z"/></svg>',
    overview:'<svg viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/></svg>',
    logs:'<svg viewBox="0 0 24 24"><path d="M5 6h14M5 12h10M5 18h7"/><circle cx="18" cy="16" r="3"/></svg>',
    members:'<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3.5 19c.6-3.1 2.4-5 5.5-5s4.9 1.9 5.5 5M16 6.5a2.5 2.5 0 1 1 0 5M16 14c2.4 0 4 1.5 4.5 4"/></svg>',
    moderation:'<svg viewBox="0 0 24 24"><path d="m14.5 4 5.5 5.5-10.5 10.5H4v-5.5zM13 5.5l5.5 5.5M4 4l16 16"/></svg>',
    announce:'<svg viewBox="0 0 24 24"><path d="M4 13v-2l13-5v12zM4 13l3 7h3l-2-6M17 9.5a3 3 0 0 1 0 5"/></svg>',
    streams:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M7 7a7 7 0 0 0 0 10M17 7a7 7 0 0 1 0 10M4 4a11 11 0 0 0 0 16M20 4a11 11 0 0 1 0 16"/></svg>',
    social:'<svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6"/></svg>',
    routing:'<svg viewBox="0 0 24 24"><path d="M5 7h14M5 12h14M5 17h14"/><circle cx="9" cy="7" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="10" cy="17" r="2"/></svg>',
    settings:'<svg viewBox="0 0 24 24"><path d="M9.5 3.8 12 3l2.5.8.8 2.5 2.1 1.5-.5 2.6.5 2.6-2.1 1.5-.8 2.5L12 21l-2.5-.8-.8-2.5-2.1-1.5.5-2.6-.5-2.6 2.1-1.5z"/><circle cx="12" cy="12" r="3"/></svg>',
    server:'<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="6" rx="2"/><rect x="4" y="14" width="16" height="6" rx="2"/><path d="M7 7h.01M7 17h.01"/></svg>'
  };
  const ensure=()=>{if(!document.querySelector('link[data-rs-favicon]')){const l=document.createElement('link');l.rel='icon';l.type='image/svg+xml';l.href='./favicon.svg?v=1';l.dataset.rsFavicon='1';document.head.appendChild(l)}if(!document.querySelector('link[data-rs-server-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='./server-polish.css?v=1';l.dataset.rsServerCss='1';document.head.appendChild(l)}};
  const run=()=>{ensure();document.querySelectorAll('.sidebar .nav').forEach(b=>{const v=b.dataset.view==='control'?'server':b.dataset.view;if(!svg[v])return;let i=b.querySelector('.nav-icon');if(!i){i=document.createElement('span');i.className='nav-icon';b.insertBefore(i,b.firstChild)}i.innerHTML=svg[v];const text=b.querySelector('span:not(.nav-icon)');if(!text){const raw=[...b.childNodes].find(n=>n.nodeType===3);if(raw)raw.remove()}});document.querySelectorAll('.social-card').forEach(c=>{if(c.querySelector('.platform-card-icon'))return;const v=c.classList.contains('twitch')?'twitch':c.classList.contains('youtube')?'youtube':c.classList.contains('kick')?'kick':c.classList.contains('x')?'x':null;if(v){const i=document.createElement('div');i.className='platform-card-icon';i.innerHTML=svg[v];c.insertBefore(i,c.firstChild)}})};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();new MutationObserver(run).observe(document.body,{childList:true,subtree:true});
})();
