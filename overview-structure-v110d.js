/* V110d: source-backed Overview composition. No inferred returns or simulated map pins. */
(function () {
  'use strict';
  const app = document.getElementById('v4app');
  if (!app || document.body.dataset.page !== 'index') return;

  function el(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = String(value);
    return node;
  }

  function link(url, label) {
    const node = el('a', 'sw-textlink', label);
    node.href = url;
    return node;
  }

  function dated(value) {
    return typeof value === 'string' && /^20\d{2}-\d{2}-\d{2}$/.test(value)
      ? value : 'Date unavailable';
  }

  function renderCoverage(host, data) {
    host.replaceChildren();
    const header = el('header', 'sw-panel-hd');
    header.append(el('h2', '', 'Exchange coverage'), link('health.html', 'Data health ↗'));
    host.append(header);

    const body = el('div', 'sw110d-coverage-body');
    const summary = data && data.schemaVersion === 1 ? data.summary : null;
    const venues = Array.isArray(data?.byVenue) ? data.byVenue : [];
    const valid = summary && Number.isInteger(summary.listings)
      && Number.isInteger(summary.datedPrice)
      && summary.listings > 0
      && summary.datedPrice >= 0
      && summary.datedPrice <= summary.listings;
    if (!valid) {
      body.append(el('p', 'sw-meta', 'Dated exchange coverage is unavailable. No values are inferred.'));
      host.append(body);
      return;
    }

    const count = el('div', 'sw110d-coverage-total');
    count.append(el('strong', '', summary.datedPrice + ' / ' + summary.listings));
    count.append(el('span', '', 'research listings have a dated price observation'));
    body.append(count);
    body.append(el('p', 'sw110d-coverage-caption',
      'By listing venue · comparison ' + dated(data.comparisonDate) + ' · not live or official certified closes'));

    const rows = el('div', 'sw110d-venue-list');
    const items = venues
      .filter(v => v && typeof v.venue === 'string' && v.venue.length < 48
        && Number.isInteger(v.listings) && v.listings > 0
        && Number.isInteger(v.datedPrice) && v.datedPrice >= 0
        && v.datedPrice <= v.listings)
      .sort((a,b) => b.listings - a.listings || a.venue.localeCompare(b.venue));
    for (const v of items) {
      const row = el('div', 'sw110d-venue');
      const heading = el('div', 'sw110d-venue-heading');
      heading.append(el('strong', '', v.venue));
      heading.append(el('span', '', v.datedPrice + ' / ' + v.listings));
      const meter = el('div', 'sw110d-venue-track');
      meter.setAttribute('role', 'meter');
      meter.setAttribute('aria-label', v.venue + ' dated-price coverage');
      meter.setAttribute('aria-valuemin', '0');
      meter.setAttribute('aria-valuemax', String(v.listings));
      meter.setAttribute('aria-valuenow', String(v.datedPrice));
      const fill = el('span', 'sw110d-venue-fill');
      fill.style.width = Math.min(100, 100 * v.datedPrice / v.listings).toFixed(1) + '%';
      meter.append(fill);
      row.append(heading,meter);
      rows.append(row);
    }
    if (items.length) body.append(rows);
    const foot = el('p', 'sw-meta sw110d-coverage-foot');
    foot.append('Venue bars show observation coverage, NOT market returns. ');
    foot.append(link('health.html', 'Inspect missing prices ↗'));
    body.append(foot);
    host.append(body);
  }

  async function updateCoverage(host) {
    try {
      const response = await fetch('data/daily-price-coverage-v105.json', {cache: 'no-store'});
      if (!response.ok) throw new Error('coverage feed unavailable');
      const data = await response.json();
      if (host.isConnected) renderCoverage(host, data);
    } catch {
      if (host.isConnected) renderCoverage(host, null);
    }
  }

  function mount() {
    const grid = app.querySelector('.sw98-market-secondary');
    const companion = grid?.querySelector('.sw110-heat-companion');
    const watch = companion?.querySelector('.sw99-watchlist');
    if (!grid || !companion || !watch || grid.dataset.sw110d === 'mounted') return false;
    grid.dataset.sw110d = 'mounted';

    const coverage = el('section', 'sw-panel sw110d-market-coverage');
    coverage.setAttribute('aria-label', 'Dated exchange coverage, not market returns');
    renderCoverage(coverage, null);
    grid.insertBefore(coverage, companion);
    updateCoverage(coverage);

    // Keep the full original movers and their source-linked company links,
    // but give the second-row map slot to factual geography/coverage.
    const movers = companion.querySelector(':scope > .sw-panel:not(.sw99-watchlist)');
    if (movers) {
      const details = el('details', 'sw110d-movers');
      const summary = el('summary', '');
      summary.append(el('strong', '', 'Biggest dated stock moves'));
      summary.append(el('span', '', 'Expand movers'));
      details.append(summary, movers);
      grid.after(details);
    }
    return true;
  }

  if (mount()) return;
  const observer = new MutationObserver(() => { if (mount()) observer.disconnect(); });
  observer.observe(app, {childList: true, subtree: true});
  window.addEventListener('pagehide', () => observer.disconnect(), {once: true});
})();
