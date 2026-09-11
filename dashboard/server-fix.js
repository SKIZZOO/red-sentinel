(()=>{
  const clean=()=>{
    const view=document.querySelector('#view-server');
    const nav=document.querySelector('.sidebar nav [data-view="control"]');
    const glyphs={server:'▤',channel:'#',role:'◇'};
    if(nav){
      const icon=nav.querySelector('.nav-icon');
      if(icon) icon.innerHTML=`<span class="server-glyph">${glyphs.server}</span>`;
    }
    if(view){
      const icons=view.querySelectorAll('.server-panel-icon');
      icons.forEach((el,i)=>{el.innerHTML=`<span class="server-glyph">${i===1?glyphs.role:(i===0?glyphs.channel:glyphs.server)}</span>`;});
      view.querySelectorAll('.server-type').forEach(el=>{
        const text=el.textContent.replace(/^\s*[#◇▤]\s*/,'').trim();
        el.innerHTML=`<span class="server-glyph server-glyph-small">#</span> ${text}`;
      });
      view.querySelectorAll('svg').forEach(el=>el.remove());
    }
    const toast=document.querySelector('#toast');
    if(toast && /Audit failed:/i.test(toast.textContent||'')){
      toast.classList.remove('show');
      const audit=document.querySelector('#scAudit');
      if(audit && !audit.querySelector('.audit-notice')) audit.innerHTML='<div class="audit-notice"><strong>Audit Log unavailable</strong><span>The bot does not have permission to view the Discord audit log.</span><small>Give the bot <b>View Audit Log</b> permission in Discord to enable audit entries.</small></div>';
    }
  };
  const style=document.createElement('style');
  style.textContent='.server-glyph{display:inline-grid!important;place-items:center!important;width:20px!important;height:20px!important;font:900 16px/1 Inter,system-ui,sans-serif!important;color:currentColor!important;transform:none!important;scale:none!important}.server-panel-icon .server-glyph{width:20px!important;height:20px!important;font-size:18px!important}.server-glyph-small{width:12px!important;height:12px!important;font-size:11px!important}.nav-icon .server-glyph{width:20px!important;height:20px!important;font-size:15px!important}.server-panel-icon{transform:none!important;scale:none!important}.server-panel-icon *{transform:none!important;scale:none!important}';
  document.head.appendChild(style);
  clean();
  new MutationObserver(clean).observe(document.body,{childList:true,subtree:true});
})();
