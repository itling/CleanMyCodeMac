(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.DiskPresentation = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function decimalGB(bytes) {
    const value = Number(bytes);
    return ((Number.isFinite(value) ? Math.max(value, 0) : 0) / 1_000_000_000).toFixed(1) + ' GB';
  }

  function diskSummary(payload, labels) {
    const total = Number(payload.total) || 0;
    const used = Number(payload.used) || 0;
    const free = Number(payload.free) || 0;
    const available = Number.isFinite(Number(payload.available)) ? Number(payload.available) : free;
    const reclaimable = Math.max(Number(payload.reclaimable) || 0, 0);
    const secondaryParts = [labels.available + ' ' + decimalGB(available)];

    if (reclaimable > 0) {
      secondaryParts.push(labels.reclaimable + ' ' + decimalGB(reclaimable));
    }

    return {
      primary: decimalGB(used).replace(' GB', '') + ' / ' + decimalGB(total),
      secondary: secondaryParts.join(' \u00b7 '),
    };
  }

  return { decimalGB, diskSummary };
}));
