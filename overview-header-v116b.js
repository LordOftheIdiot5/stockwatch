/* V116b: put truthful source freshness in spare desktop header space.
   No facts, scan times, or licence states are modified. On smaller viewports
   restore the original document order. */
(() => {
  'use strict';
  if (document.body.dataset.page !== 'index') return;
  const app = document.getElementById('v4app');
  if (!app) return;
  function sync() {
    const head = app.querySelector('.sw-overview-head');
    const source = app.querySelector('details.sw96-source-status');
    const status = app.querySelector('.sw-overview-status');
    if (!head || !source || !status) return;
    const desktop = window.matchMedia('(min-width:1320px)').matches;
    if (desktop) {
      if (source.parentElement !== head)
        head.insertBefore(source, head.querySelector('.sw-ws-actions'));
    } else if (source.previousElementSibling !== status) {
      status.insertAdjacentElement('afterend', source);
    }
  }
  let pending = false;
  function schedule() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      sync();
    });
  }
  new MutationObserver(schedule).observe(app,{childList:true,subtree:true});
  window.addEventListener('resize',schedule,{passive:true});
  schedule();
})();
