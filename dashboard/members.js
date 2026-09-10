(() => {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const state = window.rsState;
  if (!state) return;
  let members = [];
  let selected = null;

  function api(path, opts = {}) {
    const headers = Object.assign({"Content-Type":"application/json"}, opts.headers || {});
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    return fetch(state.api.replace(/\/$/, "") + path, {...opts, headers, cache:"no-store"}).then(async r => {
      if (!r.ok) throw new Error((await r.text()) || `${r.status} ${r.statusText}`);
      return r.status === 204 ? {} : r.json();
    });
  }
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const toast = t => { const e=$("#toast"); if(e){e.textContent=t;e.classList.add("show");setTimeout(()=>e.classList.remove("show"),3000);} };
  const gid = () => String(state.guild || "");

  async function loadRoles() {
    if (!gid()) return;
    try {
      const g = await api(`/api/guilds/${gid()}`);
      const select = $("#memberRole");
      if (select) select.innerHTML = `<option value="">Select a role…</option>` + (g.roles || []).sort((a,b)=>b.position-a.position).map(r => `<option value="${r.id}">${esc(r.name)}</option>`).join("");
    } catch(e) { toast("Roles failed: " + e.message); }
  }

  async function loadMembers() {
    if (!gid()) return;
    const table=$("#memberTable"), count=$("#memberCount");
    if(table) table.innerHTML = `<tr><td colspan="5">Loading members…</td></tr>`;
    try {
      const q = $("#memberSearch")?.value.trim() || "";
      const data = await api(`/api/guilds/${gid()}/members?limit=500${q ? "&q="+encodeURIComponent(q) : ""}`);
      members = data.members || [];
      if(count) count.textContent = `${members.length} shown · ${data.total ?? members.length} total · ${data.cached ?? 0} cached`;
      render();
    } catch(e) {
      if(table) table.innerHTML = `<tr><td colspan="5">Could not load members: ${esc(e.message)}</td></tr>`;
      toast("Members failed: " + e.message);
    }
  }

  function render() {
    const table=$("#memberTable"); if(!table) return;
    table.innerHTML = members.map(m => {
      const roles=(m.roles||[]).map(r=>`<span class="tag">${esc(r.name)}</span>`).join(" ") || `<span class="hint">@everyone</span>`;
      const status=m.bot ? "BOT" : (m.timeout_until ? "TIMEOUT" : "ACTIVE");
      return `<tr><td><div style="display:flex;align-items:center;gap:10px"><img src="${esc(m.avatar||"")}" alt="" width="34" height="34" style="border-radius:50%;object-fit:cover" onerror="this.style.display='none'"><div><b>${esc(m.display_name)}</b><br><small>${esc(m.name)} · ${m.id}</small></div></div></td><td><span class="tag">${status}</span></td><td>${roles}</td><td>${m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "—"}</td><td><button type="button" class="ghost member-select" data-id="${m.id}">Manage</button></td></tr>`;
    }).join("") || `<tr><td colspan="5">No members found.</td></tr>`;
    $$(".member-select").forEach(b=>b.addEventListener("click",()=>selectMember(b.dataset.id)));
  }

  function selectMember(id) {
    selected=members.find(m=>String(m.id)===String(id));
    if(!selected) return;
    $("#memberEditor").hidden=false;
    $("#memberEditorName").textContent=`${selected.display_name} · ${selected.id}`;
    $("#memberNickname").value=selected.display_name || "";
    const role=$("#memberRole"); if(role) role.value="";
    $("#memberEditor").scrollIntoView({behavior:"smooth",block:"center"});
  }

  async function action(name, extra={}) {
    if(!selected) return toast("Select a member first.");
    try {
      await api(`/api/guilds/${gid()}/members/${name}`, {method:"POST",body:JSON.stringify({user_id:selected.id, ...extra})});
      toast("Action completed");
      await loadMembers();
      const fresh=members.find(m=>String(m.id)===String(selected.id)); if(fresh) selected=fresh;
    } catch(e) { toast("Action failed: " + e.message); }
  }

  function bind() {
    $$(".nav").forEach(b=>b.addEventListener("click",()=>{ if(b.dataset.view==="members") { loadRoles(); loadMembers(); } }));
    $("#guildSelect")?.addEventListener("change",()=>setTimeout(()=>{loadRoles();loadMembers()},100));
    $("#memberRefresh")?.addEventListener("click",loadMembers);
    let timer; $("#memberSearch")?.addEventListener("input",()=>{clearTimeout(timer);timer=setTimeout(loadMembers,250)});
    $("#memberNickSave")?.addEventListener("click",()=>action("nickname",{nickname:$("#memberNickname").value}));
    $("#memberRoleAdd")?.addEventListener("click",()=>action("role_add",{role_id:$("#memberRole").value}));
    $("#memberRoleRemove")?.addEventListener("click",()=>action("role_remove",{role_id:$("#memberRole").value}));
    $("#memberTimeout")?.addEventListener("click",()=>action("timeout",{minutes:Number($("#memberTimeoutMinutes").value||60)}));
    $("#memberTimeoutClear")?.addEventListener("click",()=>action("timeout_clear"));
    $("#memberKick")?.addEventListener("click",()=>{if(confirm("Kick this member?")) action("kick")});
    $("#memberBan")?.addEventListener("click",()=>{if(confirm("Ban this member?")) action("ban")});
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bind,{once:true}); else bind();
})();
