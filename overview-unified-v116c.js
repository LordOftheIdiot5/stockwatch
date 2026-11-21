/* V116c unified Overview. Reparent only the existing layout containers.
 * Keep original child hierarchy for charts, news, watchlists, map, data,
 * source credits, filters, and keyboard handlers. No synthesized values. */
(() => {
  'use strict';
  if (document.body.dataset.page !== 'index') return;
  const app = document.getElementById('v4app');
  if (!app) return;

  function mount() {
    if (app.querySelector('.sw116c-overview-grid')) return true;
    const primary = app.querySelector('.sw98-primary');
    const secondary = app.querySelector('.sw98-market-secondary');
    if (!primary || !secondary || !primary.parentNode || primary.parentNode !== secondary.parentNode) return false;
    // V110d adds factual coverage into the secondary row. Wait for it so
    // its insertion and movers disclosure finish before the layout reparent.
    if (!secondary.querySelector('.sw110d-market-coverage') ||
        !secondary.querySelector('.sw110-heat-companion .sw99-watchlist') ||
        !secondary.querySelector('.sw-ws-heatmap .sw93-heat-inspector')) return false;
    const unified = document.createElement('section');
    unified.className = 'sw116c-overview-grid';
    unified.setAttribute('aria-label', 'Connected market overview, coverage and heatmap');
    primary.parentNode.insertBefore(unified, primary);
    unified.append(primary, secondary);
    return true;
  }
  if (mount()) return;
  const observer = new MutationObserver(() => {
    if (mount()) observer.disconnect();
  });
  observer.observe(app, {childList:true,subtree:true});
  window.addEventListener('pagehide', () => observer.disconnect(), {once:true});
})();
