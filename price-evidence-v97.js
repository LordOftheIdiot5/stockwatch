/* V97a: show source failure mode separately from dated-price availability. */
(() => {
  const host = document.getElementById('venuePriceEvidence');
  if (!host) return;
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n = x => Number.isInteger(x) ? String(x) : '—';
  fetch('data/source-health.json', {cache:'no-store'})
    .then(r => {if (!r.ok) throw Error('HTTP '+r.status); return r.json();})
    .then(health => {
      const evidence = health.priceEvidence;
      if (!evidence || !Array.isArray(evidence.byExchange)) {
        host.textContent = 'Venue-level quality evidence is unavailable in this scan. Existing price and source labels remain in effect.';
        return;
      }
      const http = health.sourceRequests?.['Yahoo prices'] || {};
      const lastHttp = http.lastSuccessAt ? esc(http.lastSuccessAt.replace('T',' ').replace(/(\+00:00|Z)$/, ' UTC')) : 'Not recorded';
      const sourceOld = evidence.byExchange.reduce((sum, x) => sum + (Number.isInteger(x.providerOlderSession) ? x.providerOlderSession : 0), 0);
      const hasSourceCounts = evidence.byExchange.some(x => Number.isInteger(x.providerOlderSession));
      const rows = evidence.byExchange.map(x => {
        const q = x.quality || {};
        return '<tr><th scope="row">'+esc(x.name)+'</th><td>'+n(x.priced)+' / '+n(x.tracked)+'</td><td>'+n(q.comparable)+'</td><td>'+n(q.unconfirmed)+'</td><td>'+n(q.older)+'</td><td>'+n(q.no_volume)+'</td><td>'+n(x.providerOlderSession)+'</td><td>'+n(x.retainedTargetDate)+'</td></tr>';
      }).join('');
      host.innerHTML =
        '<div class="sw-v97-summary"><div><span>Comparison date</span><strong>'+esc(evidence.comparisonDate)+'</strong></div>'+
        '<div><span>Provider returned older</span><strong>'+(hasSourceCounts?n(sourceOld):'Unknown')+'</strong></div>'+
        '<div><span>MICs explicitly supplied</span><strong>'+n(evidence.micProvided)+' / '+n(evidence.tracked)+'</strong></div></div>'+
        '<p class="sw-meta">Last successful price-provider HTTP response: <strong>'+lastHttp+'</strong>. Transport success does not establish a usable or licensed closing price.</p>'+
        '<div class="sw-v97-scroll"><table class="sw-v97-table"><caption>Monitored equities by exchange label, with separate retained-price and provider-response diagnostics</caption>'+
        '<thead><tr><th scope="col">Exchange</th><th scope="col">Priced / monitored</th><th scope="col">Comparable</th><th scope="col">Unconfirmed</th><th scope="col">Older</th><th scope="col">No volume</th><th scope="col">Provider older</th><th scope="col">Retained target date</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+
        '<p class="sw-meta">Provider older means the latest upstream observation is older than the stored row; the stored row remains dated and is not treated as a new completed-session signal. '+esc(evidence.method||'')+'</p>';
    })
    .catch(() => {host.textContent='Venue diagnostics could not be loaded. No values were inferred.';});
})();
