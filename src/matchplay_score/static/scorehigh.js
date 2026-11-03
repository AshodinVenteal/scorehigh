(() => {
  'use strict';
  const one = (selector, root = document) => root.querySelector(selector);
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const readSetting = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const saveSetting = (key, value) => { try { localStorage.setItem(key, value); } catch {} };
  const themeSelect = one('[data-theme-select]');
  const styleSelect = one('[data-style-select]');
  const setStyle = style => {
    const selected = style === 'portal' ? 'portal' : 'windows';
    document.documentElement.dataset.style = selected;
    one('[data-portal-stylesheet]').disabled = selected !== 'portal';
    styleSelect.value = selected;
  };
  setStyle(readSetting('scorehigh-style'));
  styleSelect.addEventListener('change', () => {
    setStyle(styleSelect.value);
    saveSetting('scorehigh-style', styleSelect.value);
  });
  const systemTheme = matchMedia('(prefers-color-scheme: dark)');
  let themePreference = readSetting('scorehigh-theme') || 'system';
  if (!['system', 'light', 'dark'].includes(themePreference)) themePreference = 'system';
  const setTheme = () => {
    const theme = themePreference === 'system' ? (systemTheme.matches ? 'dark' : 'light') : themePreference;
    document.documentElement.dataset.theme = theme;
    themeSelect.value = themePreference;
    one('meta[name="theme-color"]').content = theme === 'dark' ? '#182223' : '#173c42';
  };
  setTheme();
  one('[data-theme-settings]').hidden = false;
  themeSelect.addEventListener('change', () => {
    themePreference = themeSelect.value;
    setTheme();
    saveSetting('scorehigh-theme', themePreference);
  });
  systemTheme.addEventListener('change', setTheme);
  const displaySettings = one('.display-settings');
  document.addEventListener('click', event => {
    if (!displaySettings.contains(event.target)) displaySettings.open = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && displaySettings.open) {
      displaySettings.open = false;
      one('summary', displaySettings).focus();
    }
  });

  const openFormat = () => { if (location.hash === '#format' && one('#format')) one('#format').open = true; };
  addEventListener('hashchange', openFormat);
  all('a[href="#format"]').forEach(link => link.addEventListener('click', () => { one('#format').open = true; }));
  openFormat();

  const search = one('[data-player-search]');
  const clear = one('[data-clear-search]');
  const filterPlayers = () => {
    if (!search) return;
    const query = search.value.trim().toLocaleLowerCase();
    const entries = all('[data-player]');
    let visible = 0;
    entries.forEach(entry => {
      entry.hidden = !entry.dataset.player.toLocaleLowerCase().includes(query);
      if (!entry.hidden) visible++;
    });
    one('[data-search-empty]').hidden = !query || visible > 0;
    one('[data-player-count]').textContent = query ? `${visible} of ${entries.length} players` : `${entries.length} player${entries.length === 1 ? '' : 's'}`;
    clear.hidden = !query;
  };
  if (search) {
    one('[data-search-toolbar]').hidden = false;
    search.addEventListener('input', filterPlayers);
    clear.addEventListener('click', () => { search.value = ''; filterPlayers(); search.focus(); });
    one('[data-expand]').addEventListener('click', event => {
      const button = event.currentTarget;
      const expand = button.getAttribute('aria-pressed') !== 'true';
      all('.ranking-entry:not([hidden]) .card-details').forEach(details => { details.open = expand; });
      button.setAttribute('aria-pressed', String(expand));
      button.textContent = expand ? 'Collapse cards' : 'Expand cards';
    });
  }

  const status = one('[data-refresh-status]');
  if (!status) return;
  const refreshButton = one('[data-refresh]');
  const autoButton = one('[data-auto]');
  let auto = readSetting('scorehigh-auto') !== 'off';
  let busy = false;
  let lastUpdated = new Date(status.dataset.updatedAt);
  const staticSnapshot = status.dataset.staticSnapshot === 'true';
  let failed = false;
  const updateStatus = () => {
    autoButton.textContent = `Auto: ${auto ? 'on' : 'off'}`;
    autoButton.setAttribute('aria-pressed', String(auto));
    if (failed || busy) return;
    const time = lastUpdated.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    if (staticSnapshot) {
      const date = lastUpdated.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
      const stale = Date.now() - lastUpdated.getTime() > 15 * 60000;
      status.textContent = `Scores snapshot: ${date}, ${time} · ${auto ? 'Checks for published updates every 60 sec' : 'Update checks paused'}. Publication scheduled every 5 min; delays are possible.${stale ? ' This snapshot is more than 15 minutes old.' : ''}`;
    } else {
      status.textContent = `Fetched ${time} · ${auto ? 'Auto-refresh every 60 sec' : 'Auto-refresh paused'}. Match Play scores may be cached for up to 60 sec.`;
    }
  };
  const refresh = async (manual = false) => {
    if (busy || (!manual && (!auto || document.hidden))) return;
    // Avoid replacing a card while someone is using its links or disclosure.
    const current = one('[data-score-content]');
    if (!manual && current.contains(document.activeElement)) return;
    busy = true;
    refreshButton.disabled = true;
    status.textContent = staticSnapshot ? 'Checking published scores…' : 'Fetching scores…';
    try {
      const response = await fetch(location.href, { cache: 'no-store', headers: { 'X-Requested-With': 'ScoreHigh' }, signal: AbortSignal.timeout(25000) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const incoming = one('[data-score-content]', doc);
      const timestamp = one('[data-refresh-status]', doc);
      if (!incoming || !timestamp) throw new Error('Incomplete scoreboard');
      const expanded = new Map(all('[data-card-key]', current).map(entry => [entry.dataset.cardKey, one('details', entry)?.open]));
      all('[data-card-key]', incoming).forEach(entry => {
        const details = one('details', entry);
        if (details && expanded.has(entry.dataset.cardKey)) details.open = expanded.get(entry.dataset.cardKey);
      });
      const scrollY = window.scrollY;
      current.replaceWith(incoming);
      filterPlayers();
      window.scrollTo({ top: scrollY, behavior: 'instant' });
      lastUpdated = new Date(timestamp.dataset.updatedAt);
      failed = false;
      delete status.dataset.error;
    } catch {
      failed = true;
      status.dataset.error = 'true';
      status.textContent = 'Update failed. Previously fetched scores are still shown. Use Refresh to try again.';
    } finally {
      busy = false;
      refreshButton.disabled = false;
      updateStatus();
    }
  };
  one('[data-refresh-controls]').hidden = false;
  refreshButton.addEventListener('click', () => refresh(true));
  autoButton.addEventListener('click', () => {
    auto = !auto;
    saveSetting('scorehigh-auto', auto ? 'on' : 'off');
    updateStatus();
  });
  setInterval(() => refresh(), 60000);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && Date.now() - lastUpdated.getTime() >= 60000) refresh();
  });
  updateStatus();
})();
