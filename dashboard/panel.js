(() => {
  const q = (s) => document.querySelector(s);
  const qa = (s) => [...document.querySelectorAll(s)];

  function showView(view) {
    qa('.view').forEach((el) => el.classList.toggle('active', el.id === `view-${view}`));
    qa('.nav').forEach((el) => el.classList.toggle('active', el.dataset.view === view));
    const title = q('#pageTitle');
    if (title) title.textContent = view.charAt(0).toUpperCase() + view.slice(1);
    if (view === 'logs' && typeof window.loadLogs === 'function') window.loadLogs();
    if (view === 'overview' && typeof window.loadOverview === 'function') window.loadOverview();
    if (view === 'announce' && typeof window.fillChannels === 'function') window.fillChannels();
    if (view === 'routing' && typeof window.renderRouting === 'function') window.renderRouting();
  }

  window.navigate = showView;

  function bind() {
    qa('.nav').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        showView(button.dataset.view);
      });
    });

    const viewAll = q('#viewAllLogs');
    if (viewAll) viewAll.addEventListener('click', () => showView('logs'));

    const refresh = q('#refreshBtn');
    if (refresh) refresh.addEventListener('click', async () => {
      if (typeof window.refreshGuilds === 'function') await window.refreshGuilds();
      if (typeof window.loadOverview === 'function') await window.loadOverview();
    });

    const logRefresh = q('#logRefresh');
    if (logRefresh && typeof window.loadLogs === 'function') logRefresh.addEventListener('click', window.loadLogs);

    const logType = q('#logType');
    if (logType && typeof window.loadLogs === 'function') logType.addEventListener('change', window.loadLogs);

    const logSearch = q('#logSearch');
    if (logSearch && typeof window.renderLogs === 'function') logSearch.addEventListener('input', window.renderLogs);

    const send = q('#sendAnnounce');
    if (send && typeof window.sendAnnouncement === 'function') send.addEventListener('click', window.sendAnnouncement);

    const routing = q('#saveRouting');
    if (routing && typeof window.saveRouting === 'function') routing.addEventListener('click', window.saveRouting);

    const ban = q('#banBtn');
    if (ban && typeof window.moderate === 'function') ban.addEventListener('click', () => window.moderate('ban'));
    const kick = q('#kickBtn');
    if (kick && typeof window.moderate === 'function') kick.addEventListener('click', () => window.moderate('kick'));
    const timeout = q('#timeoutBtn');
    if (timeout && typeof window.moderate === 'function') timeout.addEventListener('click', () => window.moderate('timeout'));

    const guild = q('#guildSelect');
    if (guild) guild.addEventListener('change', () => {
      if (window.state) window.state.guild = String(guild.value || '');
      if (typeof window.loadOverview === 'function') window.loadOverview();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true });
  else bind();
})();
