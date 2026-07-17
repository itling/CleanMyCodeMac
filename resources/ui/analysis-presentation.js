(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.AnalysisPresentation = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function prepareAnalysisPresentation(options) {
    const {
      mask,
      title,
      body,
      titleText,
      loadingHTML,
      preserveContent,
    } = options;

    body.setAttribute('aria-busy', 'true');
    if (preserveContent) return;

    title.textContent = titleText;
    body.innerHTML = loadingHTML;
    mask.classList.add('show');
  }

  function escapeHTML(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderAnalysisActions(options) {
    const path = escapeHTML(options.path);
    const name = escapeHTML(options.name);
    const labels = options.labels;
    return '<button class="btn-mini" data-reveal="' + path + '">' + escapeHTML(labels.open) + '</button>' +
      '<button class="btn-mini" data-analyze-path="' + path + '">' + escapeHTML(labels.analyze) + '</button>' +
      (options.canDelete
        ? '<button class="btn-mini btn-tree-delete" data-delete-path="' + path + '" data-delete-name="' + name + '">' + escapeHTML(labels.delete) + '</button>'
        : '');
  }

  return { prepareAnalysisPresentation, renderAnalysisActions };
}));
