/* ── i18n ── */
const UI = {
  zh: {
    used: '已使用', loading: '加载中...', heroDesc: '扫描并清理 Mac 上的垃圾文件，快速释放磁盘空间',
    startupTitle: 'CleanMyCodeMac', startupSubtitle: '正在检查本地存储、准备清理工具并加载桌面界面。', startupCaption: '正在启动',
    startScan: '开始扫描', selectAll: '全选', clearAll: '清空',
    scopeTitle: '扫描范围', scopeSummary: '已选择 {n} / {t} 项',
    scanning: '正在扫描...', initializing: '初始化中...', scopeLabel: '范围',
    scanDone: '已完成：{name}', scanError: '{name} 扫描出错',
    scanKeys: {'ui.init':'初始化中...','scan.system_cache':'正在扫描系统缓存...','scan.app_cache':'正在扫描应用缓存...','scan.log':'正在扫描日志文件...','scan.download':'正在分析下载文件夹...','scan.large_file':'正在搜索大文件...','scan.trash':'正在检查废纸篓...','scan.dev_cache':'正在扫描编程工具与语言缓存...','scan.ai_models':'正在扫描大模型文件...','scan.document':'正在扫描文档文件...','scan.media':'正在扫描媒体文件...','scan.done':'已完成：{name}','scan.error':'{name} 扫描出错'},
    foundFiles: '共发现可清理文件', selectedJunk: '已选择垃圾',
    back: '返回', selectResult: '全选结果', deselectResult: '取消全选', cleanNow: '立即清理',
    cleaning: '清理中...', cleanDone: '清理完成', cleanFreed: '清理完成，释放了 {size}',
    cleanFailed: '{n} 个项目失败',
    permOk: '&#10003; 完全磁盘访问已授权', permWarn: '&#9888; 未授权完全磁盘访问',
    permTrashWarn: '废纸篓访问未授权', permPartialWarn: '部分受保护目录未授权',
    permOpen: '打开授权设置',
    diskFree: '可用',
    badgeClean: '很干净', badgeSafe: '建议清理', badgeWarn: '谨慎清理',
    expandFiles: '展开文件列表', open: '打开', analyze: '分析',
    catTotal: '共 {size}，已选择', analysisTitle: '占用分析', analyzing: '正在分析，请稍候...',
    analysisConclusion: '分析结论', sameLevelUsage: '同级目录占用', treeView: '树状占用视图',
    upperDir: '上层目录：', dirType: '目录', fileType: '文件', percent: '占比',
    finder: 'Finder', drillDown: '深入分析', copied: '已复制', copyCmd: '复制命令',
    copyFail: '复制失败，请手动复制命令', copyFailTitle: '复制失败',
    noAnalysis: '没有可展示的分析数据。', suggestedActions: '建议动作',
    dockerNoResult: '未获取到 Docker CLI 结果，可能是 Docker 未启动或命令不可用。',
    hint: '提示', gotIt: '知道了', confirm: '请确认', cancel: '取消', ok: '确认',
    about: '关于', author: '作者', email: '邮箱', version: '版本', langZh: '中文', langEn: 'EN',
    checkUpdate: '检查更新',
    updateNow: '更新', updateTo: '更新 {version}',
    alertNoScope: '请至少勾选一个扫描范围', alertNoScopeTitle: '扫描范围为空',
    alertNoItem: '请先勾选要清理的项目', alertNoItemTitle: '未选择项目',
    confirmClean: '即将清理 {n} 个项目。\n缓存/日志等安全项目将直接删除并释放磁盘空间；文档/媒体等项目将移入废纸篓（可恢复）。确认继续？', confirmCleanTitle: '确认清理',
    confirmCleanTrash: '即将永久删除 {n} 个废纸篓项目。\n删除后不可恢复，确认继续？', confirmCleanTrashTitle: '确认永久删除',
    catName: {
      system_cache: '系统垃圾', app_cache: '应用垃圾', log: '日志文件',
      download: '下载文件', large_file: '大文件', trash: '废纸篓',
      dev_cache: '编程缓存', document: '文档文件', media: '媒体文件',
    },
    catDesc: {
      system_cache: 'macOS 系统应用产生的临时缓存', app_cache: 'Chrome、VSCode 等 App 缓存',
      log: '7 天以上的崩溃报告与运行日志', download: '下载文件夹旧文件分析',
      large_file: '搜索 500MB 以上的大文件并分析占用', trash: '立即清空废纸篓释放空间',
      dev_cache: 'Node、Rust、Java 等语言缓存与 IDE 缓存', document: '扫描主目录下的文档文件', media: '扫描主目录下的图片、音频、视频',
    },
  },
  en: {
    used: 'Used', loading: 'Loading...', heroDesc: 'Scan and clean junk files on your Mac to free up disk space',
    startupTitle: 'CleanMyCodeMac', startupSubtitle: 'Inspecting local storage, preparing cleanup tools, and loading the desktop shell.', startupCaption: 'Starting Up',
    startScan: 'Start Scan', selectAll: 'Select All', clearAll: 'Clear',
    scopeTitle: 'Scan Scope', scopeSummary: '{n} / {t} selected',
    scanning: 'Scanning...', initializing: 'Initializing...', scopeLabel: 'Scope',
    scanDone: 'Done: {name}', scanError: '{name} scan error',
    scanKeys: {'ui.init':'Initializing...','scan.system_cache':'Scanning system cache...','scan.app_cache':'Scanning app cache...','scan.log':'Scanning log files...','scan.download':'Analyzing downloads folder...','scan.large_file':'Searching large files...','scan.trash':'Checking trash...','scan.dev_cache':'Scanning dev tools & language caches...','scan.ai_models':'Scanning AI model files...','scan.document':'Scanning document files...','scan.media':'Scanning media files...','scan.done':'Done: {name}','scan.error':'{name} scan error'},
    foundFiles: 'Cleanable files found', selectedJunk: 'Selected',
    back: 'Back', selectResult: 'Select All', deselectResult: 'Deselect All', cleanNow: 'Clean Now',
    cleaning: 'Cleaning...', cleanDone: 'Clean Complete', cleanFreed: 'Cleaned, freed {size}',
    cleanFailed: '{n} items failed',
    permOk: '&#10003; Full Disk Access granted', permWarn: '&#9888; Full Disk Access not granted',
    permTrashWarn: 'Trash access not granted', permPartialWarn: 'Protected folders partially not granted',
    permOpen: 'Open Settings',
    diskFree: 'free',
    badgeClean: 'Clean', badgeSafe: 'Safe to clean', badgeWarn: 'Use caution',
    expandFiles: 'Expand file list', open: 'Open', analyze: 'Analyze',
    catTotal: 'Total {size}, selected', analysisTitle: 'Usage Analysis', analyzing: 'Analyzing, please wait...',
    analysisConclusion: 'Analysis', sameLevelUsage: 'Same-level Usage', treeView: 'Tree View',
    upperDir: 'Parent dir: ', dirType: 'Directory', fileType: 'File', percent: 'Ratio',
    finder: 'Finder', drillDown: 'Drill Down', copied: 'Copied', copyCmd: 'Copy Command',
    copyFail: 'Copy failed, please copy manually', copyFailTitle: 'Copy Failed',
    noAnalysis: 'No analysis data available.', suggestedActions: 'Suggested Actions',
    dockerNoResult: 'Docker CLI result not available. Docker may not be running.',
    hint: 'Notice', gotIt: 'OK', confirm: 'Confirm', cancel: 'Cancel', ok: 'Confirm',
    about: 'About', author: 'Author', email: 'Email', version: 'Version', langZh: '中文', langEn: 'EN',
    checkUpdate: 'Check Update',
    updateNow: 'Update', updateTo: 'Update {version}',
    alertNoScope: 'Please select at least one scan scope', alertNoScopeTitle: 'No Scope Selected',
    alertNoItem: 'Please select items to clean', alertNoItemTitle: 'No Items Selected',
    confirmClean: 'About to clean {n} items.\nSafe items (caches/logs) will be permanently deleted to free disk space. Documents/media will be moved to Trash (recoverable). Continue?', confirmCleanTitle: 'Confirm Clean',
    confirmCleanTrash: 'About to permanently delete {n} trash items.\nThis action cannot be undone. Continue?', confirmCleanTrashTitle: 'Confirm Permanent Delete',
    catName: {
      system_cache: 'System Junk', app_cache: 'App Junk', log: 'Log Files',
      download: 'Downloads', large_file: 'Large Files', trash: 'Trash',
      dev_cache: 'Dev Cache', document: 'Documents', media: 'Media',
    },
    catDesc: {
      system_cache: 'Temporary cache from macOS system apps', app_cache: 'Cache from Chrome, VSCode, etc.',
      log: 'Crash reports and logs older than 7 days', download: 'Old files in Downloads folder',
      large_file: 'Search for files larger than 500MB', trash: 'Empty Trash to free space',
      dev_cache: 'Node, Rust, Java language & IDE caches', document: 'Scan document files under Home', media: 'Scan images, audio and video under Home',
    },
  },
};
let currentLang = 'zh';
function T(key) { return (UI[currentLang] || UI.en)[key] || key; }
function catName(cat) { const d = (UI[currentLang] || UI.en).catName; return d[cat] || cat; }
function catDesc(cat) { const d = (UI[currentLang] || UI.en).catDesc; return d[cat] || ''; }

const CAT_CFG = {
  system_cache: { icon: '&#9881;', color: '#F97316', bg: '#FFF7ED' },
  app_cache:    { icon: '&#9638;', color: '#3B82F6', bg: '#EFF6FF' },
  log:          { icon: '&#9776;', color: '#8B5CF6', bg: '#F5F3FF' },
  download:     { icon: '&#8595;', color: '#10B981', bg: '#ECFDF5' },
  large_file:   { icon: '&#9650;', color: '#EF4444', bg: '#FEF2F2' },
  trash:        { icon: '&#9003;', color: '#6B7280', bg: '#F3F4F6' },
  dev_cache:    { icon: '&#128187;', color: '#0EA5E9', bg: '#F0F9FF' },
  document:     { icon: '&#128196;', color: '#D97706', bg: '#FFFBEB' },
  media:        { icon: '&#127912;', color: '#EC4899', bg: '#FDF2F8' },
};
const CAT_ORDER = ['system_cache', 'log', 'app_cache', 'dev_cache', 'download', 'document', 'media', 'large_file', 'trash'];

let resultData = null;
let scanSelections = {};
let currentScanCategories = [];
let dialogResolver = null;
let lastKnownLogs = [];
let latestScanState = null;
let expandedCategories = new Set(CAT_ORDER);
let expandedSubGroups = new Set();
const initialAppMeta = window.__cleanMyCodeMacAppMeta || {};
let appMeta = {
  version: initialAppMeta.version || '1.0.0',
  version_display: initialAppMeta.version_display || ('v' + (initialAppMeta.version || '1.0.0')),
};
let updateInfo = {
  has_update: false,
  latest_version: '',
  download_url: '',
  release_url: 'https://github.com/itling/CleanMyCodeMac/releases/latest',
  current_arch: '',
  manual_only: false,
};
const startupStartedAt = Date.now();
let bridgeObjectPromise = null;

function ensureBridgeObject() {
  if (bridgeObjectPromise) return bridgeObjectPromise;
  bridgeObjectPromise = new Promise((resolve) => {
    const finish = () => {
      if (window.pywebview && window.pywebview.api) {
        resolve(window.pywebview.api);
        return true;
      }
      return false;
    };

    const onReady = () => {
      if (finish()) {
        window.removeEventListener('pywebviewready', onReady);
      }
    };

    window.addEventListener('pywebviewready', onReady);

    const poll = () => {
      if (!finish()) {
        setTimeout(poll, 50);
      }
    };

    poll();
  });
  return bridgeObjectPromise;
}

async function waitForBridgeMethod(method) {
  const api = await ensureBridgeObject();
  if (typeof api[method] === 'function') {
    return api[method];
  }

  return new Promise((resolve) => {
    const poll = () => {
      const fn = window.pywebview && window.pywebview.api && window.pywebview.api[method];
      if (typeof fn === 'function') {
        resolve(fn);
      } else {
        setTimeout(poll, 50);
      }
    };
    poll();
  });
}

async function callBridge(method, ...args) {
  const fn = await waitForBridgeMethod(method);
  return fn(...args);
}

const bridgeApi = {
  getDisk() { return callBridge('get_disk'); },
  getPermissions() { return callBridge('get_permissions'); },
  openPermissionSettings() { return callBridge('open_permission_settings'); },
  startScan(categories) { return callBridge('start_scan', categories); },
  getScanProgress() { return callBridge('get_scan_progress'); },
  getScanResult() { return callBridge('get_scan_result'); },
  selectCategory(category, appName, selected) { return callBridge('select_category', category, appName, selected); },
  selectPath(path, selected) { return callBridge('select_path', path, selected); },
  selectAll(selected) { return callBridge('select_all', selected); },
  cleanPaths(paths) { return callBridge('clean_paths', paths); },
  analyzeTarget(path) { return callBridge('analyze_target', path); },
  revealPath(path) { return callBridge('reveal_path', path); },
  getLanguage() { return callBridge('get_language'); },
  getAppMeta() { return callBridge('get_app_meta'); },
  checkForUpdates() { return callBridge('check_for_updates'); },
  openExternalUrl(url) { return callBridge('open_external_url', url); },
  setLanguage(lang) { return callBridge('set_language', lang); },
  onBootstrapReady() { return callBridge('on_bootstrap_ready'); },
};

function showView(name) {
  document.querySelectorAll('.main > div').forEach(v => { v.classList.add('hidden'); v.style.display = 'none'; });
  const el = document.getElementById('view-' + name);
  el.classList.remove('hidden');
  el.style.display = name === 'result' ? 'flex' : '';
}

function getSubGroupKey(cat, sg) {
  return cat + '::' + (sg.primary_path || sg.app_name || '');
}

function initScopes() {
  CAT_ORDER.forEach(cat => { scanSelections[cat] = true; });
  renderScopeCards();
}

function renderScopeCards() {
  const root = document.getElementById('scope-cards');
  root.innerHTML = '';
  CAT_ORDER.forEach(cat => {
    const cfg = CAT_CFG[cat];
    const card = document.createElement('div');
    card.className = 'scope-card card' + (scanSelections[cat] ? ' selected' : '');
    card.innerHTML =
      '<input type="checkbox"' + (scanSelections[cat] ? ' checked' : '') + '>' +
      '<span class="card-icon" style="color:' + cfg.color + ';background:' + cfg.bg + '">' + cfg.icon + '</span>' +
      '<h3>' + catName(cat) + '</h3>' +
      '<p>' + catDesc(cat) + '</p>';
    card.onclick = () => {
      scanSelections[cat] = !scanSelections[cat];
      renderScopeCards();
    };
    root.appendChild(card);
  });
  updateScopeSummary();
}

function updateScopeSummary() {
  const selected = getSelectedScanCategories();
  document.getElementById('scope-summary').textContent = T('scopeSummary').replace('{n}', selected.length).replace('{t}', CAT_ORDER.length);
}

function selectAllScopes(state) {
  CAT_ORDER.forEach(cat => { scanSelections[cat] = state; });
  renderScopeCards();
}

function getSelectedScanCategories() {
  return CAT_ORDER.filter(cat => scanSelections[cat]);
}

async function loadDisk() {
  const r = await bridgeApi.getDisk();
  const pct = r.total > 0 ? (r.used / r.total * 100) : 0;
  document.getElementById('gauge-pct').textContent = Math.round(pct) + '%';
  const arc = document.getElementById('gauge-arc');
  arc.style.strokeDashoffset = 236 - 236 * (pct / 100);
  arc.style.stroke = pct < 70 ? '#10B981' : pct <= 90 ? '#F59E0B' : '#EF4444';
  const usedG = (r.used / 1073741824).toFixed(1);
  const totalG = (r.total / 1073741824).toFixed(1);
  const freeG = (r.free / 1073741824).toFixed(1);
  document.getElementById('disk-info').textContent = usedG + 'G / ' + totalG + 'G (' + T('diskFree') + ' ' + freeG + 'G)';
}

async function loadPerm() {
  const r = await bridgeApi.getPermissions();
  const el = document.getElementById('perm-status');
  if (r.fda && r.trash) {
    el.innerHTML = '<span class="perm-ok">' + T('permOk') + '</span>';
    return;
  }
  const warnText = !r.trash ? T('permTrashWarn') : T('permPartialWarn');
  el.innerHTML =
    '<span class="perm-warn">&#9888; ' + warnText + '</span>' +
    '<div><button class="perm-action" onclick="openPermissionSettings()">' + T('permOpen') + '</button></div>';
}

async function openPermissionSettings() {
  await bridgeApi.openPermissionSettings();
}

function nextPaint() {
  return new Promise(resolve => {
    requestAnimationFrame(() => {
      setTimeout(resolve, 0);
    });
  });
}

async function startScan() {
  const categories = getSelectedScanCategories();
  if (categories.length === 0) {
    await showAlert(T('alertNoScope'), T('alertNoScopeTitle'));
    return;
  }
  currentScanCategories = categories;
  showView('scan');
  document.getElementById('scan-title').textContent = T('scanning');
  document.getElementById('scan-bar').style.width = '0%';
  document.getElementById('scan-pct').textContent = '0%';
  document.getElementById('scan-label').textContent = T('initializing');
  lastKnownLogs = [];
  document.getElementById('scan-log').textContent = '';
  document.getElementById('scan-scope-label').textContent = T('scopeLabel');
  document.getElementById('scan-scope').textContent = currentScanCategories.map(cat => catName(cat)).join(currentLang === 'zh' ? '、' : ', ');

  // Give the browser a chance to paint the scan view before the bridge call starts work.
  await nextPaint();

  await bridgeApi.startScan(categories);
  pollProgress();
}

async function pollProgress() {
  const r = await bridgeApi.getScanProgress();
  latestScanState = r;
  renderScanState();
  document.getElementById('scan-log').scrollTop = document.getElementById('scan-log').scrollHeight;
  if (r.status === 'done') { setTimeout(loadResult, 400); }
  else { setTimeout(pollProgress, 200); }
}

function formatScanText(key, args, fallback) {
  const scanKeys = T('scanKeys') || {};
  let text = key && scanKeys[key] ? scanKeys[key] : (fallback || '');
  const resolvedArgs = { ...(args || {}) };
  if (resolvedArgs.category) {
    resolvedArgs.name = catName(resolvedArgs.category);
  }
  Object.keys(resolvedArgs).forEach(k => {
    text = text.replace('{' + k + '}', resolvedArgs[k]);
  });
  return text;
}

function renderScanState() {
  if (!latestScanState) return;
  document.getElementById('scan-bar').style.width = latestScanState.percent + '%';
  document.getElementById('scan-pct').textContent = latestScanState.percent + '%';
  document.getElementById('scan-label').textContent = formatScanText(
    latestScanState.label_key,
    latestScanState.label_args,
    latestScanState.label
  );
  lastKnownLogs = latestScanState.logs || [];
  renderScanLog();
}

function renderScanLog() {
  const logEl = document.getElementById('scan-log');
  if (!logEl) return;
  logEl.textContent = lastKnownLogs.map(l => {
    return '\u25b8 ' + formatScanText(l.key, l.args, l.key || '');
  }).join('\n');
}

function safetyBadge(is_safe, size) {
  if (size === 0) return '<span class="badge-clean">' + T('badgeClean') + '</span>';
  if (is_safe) return '<span class="badge badge-safe">' + T('badgeSafe') + '</span>';
  return '<span class="badge badge-warn">' + T('badgeWarn') + '</span>';
}

async function loadResult(showResultView = true) {
  resultData = await bridgeApi.getScanResult();
  if (!resultData) return;
  renderResult();
  if (showResultView) showView('result');
  await loadDisk();
}

function renderResult() {
  const r = resultData;
  document.getElementById('result-total').textContent = r.total_size;
  document.getElementById('result-selected').textContent = r.selected_size;

  const list = document.getElementById('cat-list');
  list.innerHTML = '';

  for (const cat of CAT_ORDER) {
    const data = r.categories[cat];
    if (!data) continue;
    const cfg = CAT_CFG[cat] || { icon: '?', color: '#999', bg: '#F5F5F5' };

    const group = document.createElement('div');
    group.className = 'cat-group';
    group.dataset.cat = cat;
    const isCategoryExpanded = expandedCategories.has(cat);

    const header = document.createElement('div');
    header.className = 'cat-header';
    header.innerHTML =
      '<input type="checkbox" class="cat-check"' + (data.all_selected ? ' checked' : '') + '>' +
      '<div class="cat-icon" style="background:' + cfg.bg + ';color:' + cfg.color + '">' + cfg.icon + '</div>' +
      '<span class="cat-name" style="color:' + cfg.color + '">' + catName(cat) + '</span>' +
      '<span class="cat-meta">&nbsp;&nbsp;' + T('catTotal').replace('{size}', data.size_display) + ' <span class="sel-size cat-sel-size">' + data.selected_display + '</span></span>' +
      '<span class="cat-right"><span class="cat-arrow' + (isCategoryExpanded ? ' open' : '') + '">&#9660;</span></span>';

    const body = document.createElement('div');
    body.className = 'cat-body' + (isCategoryExpanded ? '' : ' hidden');

    header.onclick = () => {
      body.classList.toggle('hidden');
      const isExpanded = !body.classList.contains('hidden');
      header.querySelector('.cat-arrow').classList.toggle('open', isExpanded);
      if (isExpanded) expandedCategories.add(cat);
      else expandedCategories.delete(cat);
    };

    const catCb = header.querySelector('.cat-check');
    catCb.indeterminate = data.any_selected && !data.all_selected;
    catCb.addEventListener('click', e => e.stopPropagation());
    catCb.addEventListener('change', async () => {
      await bridgeApi.selectCategory(cat, null, catCb.checked);
      await loadResult();
    });

    if (cat === 'trash') {
      for (const sg of data.sub_groups) {
        for (const f of sg.files) {
          const frow = document.createElement('div');
          frow.className = 'file-row';
          frow.innerHTML =
            '<input type="checkbox" class="file-cb"' + (f.selected ? ' checked' : '') +
            ' data-path="' + escapeHtml(f.path) + '">' +
            '<div class="file-path-wrap">' +
              '<div class="file-path" title="' + escapeHtml(f.path) + '">' + escapeHtml(f.path_short) + '</div>' +
              '<div class="file-hint">' + escapeHtml(f.description || '') + '</div>' +
            '</div>' +
            '<span class="file-size">' + f.size_display + '</span>' +
            '<span class="file-actions">' +
              '<button class="btn-mini" data-action="reveal" data-path="' + escapeHtml(f.path) + '">' + T('open') + '</button>' +
            '</span>';
          const fcb = frow.querySelector('.file-cb');
          fcb.addEventListener('change', async (e) => {
            e.stopPropagation();
            await bridgeApi.selectPath(f.path, fcb.checked);
            await loadResult();
          });
          frow.querySelectorAll('.btn-mini').forEach(btn => {
            btn.addEventListener('click', async (e) => {
              e.stopPropagation();
              await bridgeApi.revealPath(btn.dataset.path);
            });
          });
          body.appendChild(frow);
        }
      }
      group.appendChild(header);
      group.appendChild(body);
      list.appendChild(group);
      continue;
    }

    for (const sg of data.sub_groups) {
      const subGroupKey = getSubGroupKey(cat, sg);
      const isSubGroupExpanded = expandedSubGroups.has(subGroupKey);
      const subRow = document.createElement('div');
      subRow.className = 'sub-item';
      subRow.innerHTML =
        '<input type="checkbox" class="sub-cb"' +
        (sg.all_selected ? ' checked' : '') +
        (sg.any_selected && !sg.all_selected ? ' data-indeterminate="1"' : '') +
        ' data-cat="' + cat + '" data-app="' + escapeHtml(sg.app_name) + '">' +
        '<span class="sub-name">' + escapeHtml(sg.app_name) + '</span>' +
        '<span class="sub-desc">' + escapeHtml(sg.description) + '</span>' +
        '<span class="sub-right">' +
          '<span class="sub-size">' + sg.size_display + '</span>' +
          safetyBadge(sg.is_safe, sg.size) +
          '<span class="sub-toggle' + (isSubGroupExpanded ? ' open' : '') + '" title="' + T('expandFiles') + '">&#9660;</span>' +
        '</span>';

      const cb = subRow.querySelector('.sub-cb');
      if (cb.dataset.indeterminate === '1') cb.indeterminate = true;
      cb.addEventListener('change', async (e) => {
        e.stopPropagation();
        await bridgeApi.selectCategory(cat, sg.app_name, cb.checked);
        await loadResult();
      });

      body.appendChild(subRow);

      const filesDiv = document.createElement('div');
      filesDiv.className = 'file-details' + (isSubGroupExpanded ? '' : ' hidden');
      for (const f of sg.files) {
        const frow = document.createElement('div');
        frow.className = 'file-row';
        frow.innerHTML =
          '<input type="checkbox" class="file-cb"' + (f.selected ? ' checked' : '') +
          ' data-path="' + escapeHtml(f.path) + '">' +
          '<div class="file-path-wrap">' +
            '<div class="file-path" title="' + escapeHtml(f.path) + '">' + escapeHtml(f.path_short) + '</div>' +
          '</div>' +
          '<span class="file-size">' + f.size_display + '</span>' +
          '<span class="file-actions">' +
            '<button class="btn-mini" data-action="reveal" data-path="' + escapeHtml(f.path) + '">' + T('open') + '</button>' +
            (f.can_analyze ? '<button class="btn-mini" data-action="analyze" data-path="' + escapeHtml(f.path) + '">' + T('analyze') + '</button>' : '') +
          '</span>';
        const fcb = frow.querySelector('.file-cb');
        fcb.addEventListener('change', async (e) => {
          e.stopPropagation();
          await bridgeApi.selectPath(f.path, fcb.checked);
          await loadResult();
        });
        frow.querySelectorAll('.btn-mini').forEach(btn => {
          btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const targetPath = btn.dataset.path;
            if (btn.dataset.action === 'reveal') {
              await bridgeApi.revealPath(targetPath);
            } else if (btn.dataset.action === 'analyze') {
              await openAnalysis(targetPath);
            }
          });
        });
        filesDiv.appendChild(frow);
      }
      const toggle = subRow.querySelector('.sub-toggle');
      toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        filesDiv.classList.toggle('hidden');
        const isExpanded = !filesDiv.classList.contains('hidden');
        toggle.classList.toggle('open', isExpanded);
        if (isExpanded) expandedSubGroups.add(subGroupKey);
        else expandedSubGroups.delete(subGroupKey);
      });
      body.appendChild(filesDiv);
    }

    group.appendChild(header);
    group.appendChild(body);
    list.appendChild(group);
  }
}

async function toggleAllResultSelection(state) {
  await bridgeApi.selectAll(state);
  await loadResult();
}

async function doClean() {
  // 从 resultData 收集所有服务端标记为 selected 的路径
  const paths = [];
  let hasTrashItems = false;
  if (resultData) {
    for (const cat of CAT_ORDER) {
      const data = resultData.categories[cat];
      if (!data) continue;
      for (const sg of data.sub_groups) {
        for (const f of sg.files) {
          if (f.selected && !paths.includes(f.path)) {
            paths.push(f.path);
            if (cat === 'trash') hasTrashItems = true;
          }
        }
      }
    }
  }
  const uniquePaths = paths;

  if (uniquePaths.length === 0) {
    await showAlert(T('alertNoItem'), T('alertNoItemTitle'));
    return;
  }
  const confirmed = await showConfirm(
    (hasTrashItems ? T('confirmCleanTrash') : T('confirmClean')).replace('{n}', uniquePaths.length),
    hasTrashItems ? T('confirmCleanTrashTitle') : T('confirmCleanTitle')
  );
  if (!confirmed) return;

  const btn = document.getElementById('btn-clean');
  btn.disabled = true;
  btn.textContent = T('cleaning');

  const r = await bridgeApi.cleanPaths(uniquePaths);

  let msg = T('cleanFreed').replace('{size}', r.freed);
  if (r.errors > 0) msg += '\n\n' + T('cleanFailed').replace('{n}', r.errors);
  showToast(msg, T('cleanDone'), 'success');
  btn.disabled = false;
  btn.textContent = T('cleanNow');
  await new Promise(resolve => setTimeout(resolve, 600));
  await loadDisk();
  startScan();
}

async function openAnalysis(path) {
  const mask = document.getElementById('analysis-mask');
  const title = document.getElementById('analysis-title');
  const body = document.getElementById('analysis-body');
  title.textContent = T('analysisTitle');
  body.innerHTML = '<div class="analysis-note">' + T('analyzing') + '</div>';
  mask.classList.add('show');

  const data = await bridgeApi.analyzeTarget(path);
  if (data.error) {
    title.textContent = T('analysisTitle');
    body.innerHTML = '<div class="analysis-note">' + escapeHtml(data.error) + '</div>';
    return;
  }

  title.textContent = data.name + ' · ' + data.size_display;

  const sections = [];
  if (data.highlights) {
    sections.push(
      '<div class="analysis-section"><h4>' + T('analysisConclusion') + '</h4>' +
      data.highlights.map(line => '<div class="analysis-note">' + escapeHtml(line) + '</div>').join('') +
      '</div>'
    );
  }

  if (data.same_level_items && data.same_level_items.length) {
    sections.push(renderAnalysisList(T('sameLevelUsage'), data.same_level_items));
  }

  if (data.tree) {
    sections.push(renderAnalysisTree(T('treeView'), data.tree));
  }

  if (data.ancestor_levels && data.ancestor_levels.length) {
    data.ancestor_levels.forEach(level => {
      if (level.children && level.children.length) {
        sections.push(renderAnalysisList(T('upperDir') + level.path, level.children));
      }
    });
  }

  if (data.special && data.special.kind === 'docker_raw') {
    sections.push(
      '<div class="analysis-section"><h4>' + escapeHtml(data.special.title) + '</h4>' +
      data.special.highlights.map(line => '<div class="analysis-note">' + escapeHtml(line) + '</div>').join('') +
      (data.special.docker_summary && data.special.docker_summary.length
        ? '<div class="analysis-chip-row">' + data.special.docker_summary.map(item =>
            '<div class="analysis-chip">' + escapeHtml(item.label) + ': ' + escapeHtml(item.value) + '</div>'
          ).join('') + '</div>'
        : '') +
      (data.special.suggestions && data.special.suggestions.length
        ? '<div class="analysis-section"><h4>' + T('suggestedActions') + '</h4>' +
          data.special.suggestions.map(item =>
            '<div class="analysis-cmd">' +
              '<div class="analysis-cmd-title">' + escapeHtml(item.label) + '</div>' +
              '<div class="analysis-cmd-desc">' + escapeHtml(item.description) + '</div>' +
              '<div class="analysis-cmd-code">' + escapeHtml(item.command) + '</div>' +
              '<div class="analysis-cmd-actions">' +
                '<button class="btn-mini" data-copy="' + escapeHtml(item.command) + '">' + T('copyCmd') + '</button>' +
              '</div>' +
            '</div>'
          ).join('') +
          '</div>'
        : '') +
      (data.special.docker_cli_available
        ? '<div class="analysis-pre">' + escapeHtml(data.special.docker_df_lines.join('\n')) + '</div>'
        : '<div class="analysis-note">' + T('dockerNoResult') + '</div>') +
      '</div>'
    );
  }

  body.innerHTML = sections.join('') || '<div class="analysis-note">' + T('noAnalysis') + '</div>';
  bindTreeToggles();
  bindAnalysisActions();
}

function renderAnalysisList(title, items) {
  return '<div class="analysis-section"><h4>' + escapeHtml(title) + '</h4><div class="analysis-list">' +
    items.map(item =>
      '<div class="analysis-row">' +
        '<div class="analysis-name" title="' + escapeHtml(item.path || item.name) + '">' + escapeHtml(item.name) + '</div>' +
        '<div class="analysis-size">' + escapeHtml(item.size_display) + '</div>' +
      '</div>'
    ).join('') +
    '</div></div>';
}

function renderAnalysisTree(title, tree) {
  return '<div class="analysis-section"><h4>' + escapeHtml(title) + '</h4><div class="tree-root">' +
    renderTreeNode(tree, 0) +
    '</div></div>';
}

function renderTreeNode(node, depth) {
  const hasChildren = node.children && node.children.length > 0;
  return '<div class="tree-node tree-depth-' + depth + '">' +
    '<div class="tree-head">' +
      '<span class="tree-toggle"' + (hasChildren ? '' : ' style="visibility:hidden"') + '>' + (hasChildren ? '&#9660;' : '') + '</span>' +
      '<div class="tree-label">' +
        '<div class="tree-name" title="' + escapeHtml(node.path) + '">' + escapeHtml(node.name) + '</div>' +
        '<div class="tree-meta">' + escapeHtml(node.kind === 'dir' ? T('dirType') : T('fileType')) + ' · ' + T('percent') + ' ' + escapeHtml(node.percent) + '</div>' +
      '</div>' +
      '<div class="tree-actions">' +
        '<button class="btn-mini" data-reveal="' + escapeHtml(node.path) + '">' + T('finder') + '</button>' +
        (node.can_drill ? '<button class="btn-mini" data-drill="' + escapeHtml(node.path) + '">' + T('drillDown') + '</button>' : '') +
      '</div>' +
      '<div class="tree-size">' + escapeHtml(node.size_display) + '</div>' +
    '</div>' +
    (hasChildren ? '<div class="tree-children">' + node.children.map(child => renderTreeNode(child, depth + 1)).join('') + '</div>' : '') +
    '</div>';
}

function bindTreeToggles() {
  document.querySelectorAll('.tree-node > .tree-head > .tree-toggle').forEach(toggle => {
    if (!toggle.textContent.trim()) return;
    toggle.addEventListener('click', () => {
      const node = toggle.closest('.tree-node');
      const children = node.querySelector(':scope > .tree-children');
      if (!children) return;
      children.classList.toggle('hidden');
      toggle.innerHTML = children.classList.contains('hidden') ? '&#9658;' : '&#9660;';
    });
  });
}

function bindAnalysisActions() {
  document.querySelectorAll('[data-drill]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await openAnalysis(btn.dataset.drill);
    });
  });

  document.querySelectorAll('[data-reveal]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await bridgeApi.revealPath(btn.dataset.reveal);
    });
  });

  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = T('copied');
        setTimeout(() => { btn.textContent = T('copyCmd'); }, 1200);
      } catch (_) {
        showAlert(T('copyFail'), T('copyFailTitle'));
      }
    });
  });
}

function showAlert(message, title) {
  title = title || T('hint');
  return new Promise(resolve => {
    const mask = document.getElementById('dialog-mask');
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-body').textContent = message;
    document.getElementById('dialog-actions').innerHTML =
      '<button class="btn-dialog-primary" onclick="closeDialog(true)">' + T('gotIt') + '</button>';
    dialogResolver = resolve;
    mask.classList.add('show');
  });
}

function showConfirm(message, title) {
  title = title || T('confirm');
  return new Promise(resolve => {
    const mask = document.getElementById('dialog-mask');
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-body').textContent = message;
    document.getElementById('dialog-actions').innerHTML =
      '<button class="btn-dialog-secondary" onclick="closeDialog(false)">' + T('cancel') + '</button>' +
      '<button class="btn-dialog-primary" onclick="closeDialog(true)">' + T('ok') + '</button>';
    dialogResolver = resolve;
    mask.classList.add('show');
  });
}

function closeDialog(result) {
  const mask = document.getElementById('dialog-mask');
  mask.classList.remove('show');
  if (dialogResolver) {
    const resolver = dialogResolver;
    dialogResolver = null;
    resolver(Boolean(result));
  }
}

function showToast(message, title, type) {
  title = title || T('hint');
  type = type || 'success';
  const wrap = document.getElementById('toast-wrap');
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.innerHTML =
    '<div class="toast-title">' + escapeHtml(title) + '</div>' +
    '<div class="toast-body">' + escapeHtml(message) + '</div>';
  wrap.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 220);
  }, 3200);
}

function closeAnalysis(event) {
  if (event && event.target !== document.getElementById('analysis-mask')) return;
  document.getElementById('analysis-mask').classList.remove('show');
}

function escapeHtml(s) { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

async function notifyBootstrapReady() {
  try {
    await bridgeApi.onBootstrapReady();
  } catch (_) {}
}

async function hideStartupScreen() {
  const minVisibleMs = 650;
  const elapsed = Date.now() - startupStartedAt;
  if (elapsed < minVisibleMs) {
    await new Promise(resolve => setTimeout(resolve, minVisibleMs - elapsed));
  }
  const startup = document.getElementById('startup-screen');
  startup.classList.add('hidden');
}

function renderLangSwitch() {
  const el = document.getElementById('lang-switch');
  el.innerHTML =
    '<button class="lang-btn' + (currentLang === 'zh' ? ' active' : '') + '" onclick="switchLang(\'zh\')">' + T('langZh') + '</button>' +
    '<button class="lang-btn' + (currentLang === 'en' ? ' active' : '') + '" onclick="switchLang(\'en\')">' + T('langEn') + '</button>';
}

function applyAppMeta() {
  const versionValue = document.getElementById('version-value');
  if (versionValue) {
    versionValue.textContent = appMeta.version_display || ('v' + (appMeta.version || '1.0.0'));
  }
}

function applyUpdateInfo() {
  const button = document.getElementById('update-btn');
  if (!button) return;

  if (!updateInfo.has_update || !updateInfo.download_url) {
    if (updateInfo.manual_only && updateInfo.release_url) {
      button.textContent = T('checkUpdate');
      button.title = updateInfo.release_url;
      button.classList.remove('hidden');
      return;
    }

    button.classList.add('hidden');
    button.textContent = '';
    button.title = '';
    return;
  }

  const version = updateInfo.latest_version ? ('v' + updateInfo.latest_version) : '';
  button.textContent = T('updateNow');
  button.title = T('updateTo').replace('{version}', version);
  button.classList.remove('hidden');
}

function applyLang() {
  renderLangSwitch();
  document.getElementById('startup-title').textContent = T('startupTitle');
  document.getElementById('startup-subtitle').textContent = T('startupSubtitle');
  document.getElementById('startup-caption').textContent = T('startupCaption');
  document.getElementById('gauge-label').textContent = T('used');
  document.getElementById('disk-info').textContent = T('loading');
  document.getElementById('hero-desc').textContent = T('heroDesc');
  document.getElementById('btn-start-scan').textContent = T('startScan');
  document.getElementById('btn-select-all').textContent = T('selectAll');
  document.getElementById('btn-clear-all').textContent = T('clearAll');
  document.getElementById('scope-title').textContent = T('scopeTitle');
  document.getElementById('scan-title').textContent = T('scanning');
  document.getElementById('scan-scope-label').textContent = T('scopeLabel');
  if (currentScanCategories.length > 0) {
    document.getElementById('scan-scope').textContent = currentScanCategories.map(cat => catName(cat)).join(currentLang === 'zh' ? '、' : ', ');
  }
  const scanViewVisible = !document.getElementById('view-scan').classList.contains('hidden');
  if (scanViewVisible) {
    renderScanState();
  }
  document.getElementById('result-found-label').textContent = T('foundFiles');
  document.getElementById('result-selected-label').textContent = T('selectedJunk');
  document.getElementById('btn-back').textContent = T('back');
  document.getElementById('btn-select-result').textContent = T('selectResult');
  document.getElementById('btn-deselect-result').textContent = T('deselectResult');
  document.getElementById('btn-clean').textContent = T('cleanNow');
  document.getElementById('about-label').textContent = T('about');
  document.getElementById('author-label').textContent = T('author');
  document.getElementById('email-label').textContent = T('email');
  document.getElementById('version-label').textContent = T('version');
  applyAppMeta();
  applyUpdateInfo();
  renderScopeCards();
  loadDisk();
  loadPerm();
  if (resultData) renderResult();
}

async function switchLang(lang) {
  currentLang = lang;
  await bridgeApi.setLanguage(lang);
  applyLang();
  const resultViewVisible = !document.getElementById('view-result').classList.contains('hidden');
  if (resultData && resultViewVisible) {
    await loadResult(false);
  }
}

async function initLang() {
  try {
    const r = await bridgeApi.getLanguage();
    currentLang = r.lang || currentLang;
  } catch (_) {}
}

async function loadAppMeta() {
  try {
    const r = await bridgeApi.getAppMeta();
    if (r && typeof r === 'object') {
      appMeta = {
        version: r.version || appMeta.version,
        version_display: r.version_display || appMeta.version_display,
      };
      applyAppMeta();
    }
  } catch (_) {}
}

async function loadUpdateInfo() {
  try {
    const r = await bridgeApi.checkForUpdates();
    if (r && typeof r === 'object') {
      updateInfo = {
        has_update: Boolean(r.has_update),
        latest_version: r.latest_version || '',
        download_url: r.download_url || r.release_url || '',
        release_url: r.release_url || updateInfo.release_url,
        current_arch: r.current_arch || '',
        manual_only: Boolean(r.manual_only),
      };
      applyUpdateInfo();
    }
  } catch (_) {
    updateInfo = {
      ...updateInfo,
      has_update: false,
      manual_only: true,
      download_url: '',
    };
    applyUpdateInfo();
  }
}

async function openUpdateDownload() {
  const target = updateInfo.download_url || updateInfo.release_url;
  if (!target) return;
  await bridgeApi.openExternalUrl(target);
}

function bootstrapApp() {
  initScopes();
  applyLang();
  hideStartupScreen();
  notifyBootstrapReady();
  Promise.all([initLang(), loadAppMeta()]).then(() => {
    applyLang();
    loadUpdateInfo();
  });
}

bootstrapApp();
