const ui = {
  status: document.getElementById('status'),
  recent: document.getElementById('recent'),
  details: document.getElementById('details'),
  searchForm: document.getElementById('searchForm'),
  searchInput: document.getElementById('searchInput'),
  autocomplete: document.getElementById('autocomplete'),
  viewAllBtn: document.getElementById('viewAllBtn'),
  referenceBtn: document.getElementById('referenceBtn'),
  modalBackdrop: document.getElementById('modalBackdrop'),
  referenceModal: document.getElementById('referenceModal'),
  modalClose: document.getElementById('modalClose'),
  tabVertex: document.getElementById('tabVertex'),
  tabEdge: document.getElementById('tabEdge'),
  refFilter: document.getElementById('refFilter'),
  refList: document.getElementById('refList'),
  hideDisconnected: document.getElementById('hideDisconnected'),
  keepSelected: document.getElementById('keepSelected'),
  hideSelected: document.getElementById('hideSelected'),
  clearRel: document.getElementById('clearRel'),
  resetType: document.getElementById('resetType'),
  relNote: document.getElementById('relNote'),
  relOut: document.getElementById('relOut'),
  relIn: document.getElementById('relIn'),
  navMode: document.getElementById('navMode'),
  clearAllVisibility: document.getElementById('clearAllVisibility'),
  layoutMode: document.getElementById('layoutMode'),
  autoLayout: document.getElementById('autoLayout'),
  sidebarLeft: document.getElementById('sidebarLeft'),
  sidebarRight: document.getElementById('sidebarRight'),
  collapseLeft: document.getElementById('collapseLeft'),
  collapseRight: document.getElementById('collapseRight'),
  resizerLeft: document.getElementById('resizerLeft'),
  resizerRight: document.getElementById('resizerRight'),
  expandLeft: document.getElementById('expandLeft'),
  expandRight: document.getElementById('expandRight'),
  tabSchema: document.getElementById('tabSchema'),
  tabInstance: document.getElementById('tabInstance'),
  schemaPanel: document.getElementById('schemaPanel'),
  instancePanel: document.getElementById('instancePanel'),
  instanceForm: document.getElementById('instanceForm'),
  instanceInput: document.getElementById('instanceInput'),
  instanceScope: document.getElementById('instanceScope'),
  instanceQuery: document.getElementById('instanceQuery'),
  instanceResults: document.getElementById('instanceResults'),
  instanceMeta: document.getElementById('instanceMeta'),
  instanceRun: document.getElementById('instanceRun'),
  instanceGenerate: document.getElementById('instanceGenerate'),
  instanceEdit: document.getElementById('instanceEdit'),
  activeGraphName: document.getElementById('activeGraphName'),
};

// Sidebar state + idempotent apply() so collapse/expand is predictable.
const sidebarState = {
  left: { collapsed: false, width: 360 },
  right: { collapsed: false, width: 360 },
};

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

function loadSidebarState() {
  try {
    const raw = localStorage.getItem('ew.sidebarState');
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed?.left?.width) sidebarState.left.width = parsed.left.width;
    if (parsed?.right?.width) sidebarState.right.width = parsed.right.width;
    if (typeof parsed?.left?.collapsed === 'boolean') sidebarState.left.collapsed = parsed.left.collapsed;
    if (typeof parsed?.right?.collapsed === 'boolean') sidebarState.right.collapsed = parsed.right.collapsed;
  } catch {
    // ignore
  }
}

function saveSidebarState() {
  try {
    localStorage.setItem('ew.sidebarState', JSON.stringify(sidebarState));
  } catch {
    // ignore
  }
}

const DEBUG = false;

document.querySelectorAll('details.section').forEach((el) => {
  el.removeAttribute('open');
});

const tooltipEl = document.createElement('div');
tooltipEl.id = 'tooltip';
tooltipEl.className = 'tooltip hidden';
document.body.appendChild(tooltipEl);

function showTooltip(text, x, y) {
  if (!text) return;
  tooltipEl.textContent = text;
  tooltipEl.classList.remove('hidden');
  const offset = 12;
  tooltipEl.style.left = `${x + offset}px`;
  tooltipEl.style.top = `${y + offset}px`;
}

function hideTooltip() {
  tooltipEl.classList.add('hidden');
}

function debug(...args) {
  if (!DEBUG) return;
  // eslint-disable-next-line no-console
  console.log('[ew-types]', ...args);
}

function setStatus(msg) {
  ui.status.textContent = msg;
}

function setSearchPlaceholder(graphLabel) {
  if (!ui.searchInput) return;
  const label = graphLabel ? String(graphLabel).trim() : '';
  const suffix = label ? ` in ${label}` : '';
  ui.searchInput.placeholder = `Search types${suffix} (e.g. CUSTOMER, METER, HAS_SERVICE)`;
}

function setMainTab(tab) {
  const isSchema = tab === 'schema';
  ui.tabSchema?.classList.toggle('active', isSchema);
  ui.tabInstance?.classList.toggle('active', !isSchema);
  ui.schemaPanel?.classList.toggle('hidden', !isSchema);
  ui.instancePanel?.classList.toggle('hidden', isSchema);
  if (isSchema) {
    scheduleGraphResize();
  }
}

function attachResizer(resizerEl, cssVar, minWidth, maxWidth, getBaseWidth) {
  if (!resizerEl) return;
  let resizing = false;

  const onMove = (e) => {
    if (!resizing) return;
    const baseWidth = getBaseWidth(e.clientX);
    const width = Math.max(minWidth, Math.min(maxWidth, baseWidth));
    document.documentElement.style.setProperty(cssVar, `${width}px`);

    // Keep JS state in sync with live resize.
    if (cssVar === '--sidebar-left-width') sidebarState.left.width = width;
    if (cssVar === '--sidebar-right-width') sidebarState.right.width = width;
  };

  const stop = () => {
    resizing = false;
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', stop);
    saveSidebarState();
    scheduleGraphResize();
  };

  resizerEl.addEventListener('mousedown', () => {
    resizing = true;
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', stop);
  });
}

attachResizer(
  ui.resizerLeft,
  '--sidebar-left-width',
  260,
  520,
  (x) => x,
);

attachResizer(
  ui.resizerRight,
  '--sidebar-right-width',
  260,
  520,
  (x) => window.innerWidth - x,
);

function applySidebarLayout() {
  const rootStyle = document.documentElement.style;

  // Ensure sane bounds if localStorage got weird.
  sidebarState.left.width = clamp(Number(sidebarState.left.width) || 360, 260, 520);
  sidebarState.right.width = clamp(Number(sidebarState.right.width) || 360, 260, 520);

  const leftW = sidebarState.left.collapsed ? 0 : sidebarState.left.width;
  const rightW = sidebarState.right.collapsed ? 0 : sidebarState.right.width;

  rootStyle.setProperty('--sidebar-left-width', `${leftW}px`);
  rootStyle.setProperty('--resizer-left-width', sidebarState.left.collapsed ? '0px' : '10px');

  rootStyle.setProperty('--sidebar-right-width', `${rightW}px`);
  rootStyle.setProperty('--resizer-right-width', sidebarState.right.collapsed ? '0px' : '10px');

  ui.sidebarLeft?.classList.toggle('sidebarCollapsed', sidebarState.left.collapsed);
  ui.resizerLeft?.classList.toggle('sidebarCollapsed', sidebarState.left.collapsed);
  ui.expandLeft?.classList.toggle('hidden', !sidebarState.left.collapsed);
  if (ui.collapseLeft) ui.collapseLeft.textContent = sidebarState.left.collapsed ? '⟩' : '⟨';

  ui.sidebarRight?.classList.toggle('sidebarCollapsed', sidebarState.right.collapsed);
  ui.resizerRight?.classList.toggle('sidebarCollapsed', sidebarState.right.collapsed);
  ui.expandRight?.classList.toggle('hidden', !sidebarState.right.collapsed);
  if (ui.collapseRight) ui.collapseRight.textContent = sidebarState.right.collapsed ? '⟨' : '⟩';

  saveSidebarState();
  scheduleGraphResize();
}

function setSidebarCollapsed(side, collapsed) {
  if (side === 'left') sidebarState.left.collapsed = collapsed;
  else sidebarState.right.collapsed = collapsed;
  applySidebarLayout();
}

function scheduleGraphResize() {
  window.requestAnimationFrame(() => {
    if (typeof cy === 'undefined') return;
    const container = cy.container();
    if (!container || container.clientWidth === 0 || container.clientHeight === 0) return;
    cy.resize();
  });
}

ui.collapseLeft?.addEventListener('click', () => {
  setSidebarCollapsed('left', !sidebarState.left.collapsed);
});

ui.collapseRight?.addEventListener('click', () => {
  setSidebarCollapsed('right', !sidebarState.right.collapsed);
});

ui.expandLeft?.addEventListener('click', () => setSidebarCollapsed('left', false));
ui.expandRight?.addEventListener('click', () => setSidebarCollapsed('right', false));

ui.tabSchema?.addEventListener('click', () => setMainTab('schema'));
ui.tabInstance?.addEventListener('click', () => setMainTab('instance'));

// Initialize sidebar layout after handlers are set.
loadSidebarState();
applySidebarLayout();

function pretty(obj) {
  return JSON.stringify(obj, null, 2);
}

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

async function apiPost(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

const cy = cytoscape({
  container: document.getElementById('cy'),
  elements: [],
  style: [
    {
      selector: 'node',
      style: {
        'background-color': '#7aa2ff',
        label: 'data(display_name)',
        'text-margin-y': -6,
        color: '#e8eefc',
        'text-outline-color': '#0b1220',
        'text-outline-width': 2,
        'font-size': 10,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 2,
        'overlay-padding': 8,
        'line-color': '#223152',
        'target-arrow-color': '#223152',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        label: 'data(display_name)',
        'text-margin-y': -4,
        'font-size': 9,
        color: '#9db0d6',
        'text-background-color': '#0b1220',
        'text-background-opacity': 0.8,
        'text-background-padding': 2,
      },
    },
    {
      selector: '.center',
      style: {
        'background-color': '#ffd166',
      },
    },
    {
      selector: ':selected',
      style: {
        'border-width': 4,
        'border-color': '#ffd166',
        'underlay-color': '#7aa2ff',
        'underlay-opacity': 0.28,
        'underlay-padding': 6,
      },
    },
    {
      selector: 'node:selected',
      style: {
        width: 38,
        height: 38,
        'font-size': 10,
      },
    },
    {
      selector: 'edge:selected',
      style: {
        width: 4,
        'line-color': '#ffd166',
        'target-arrow-color': '#ffd166',
        color: '#e8eefc',
        'text-background-color': '#132348',
      },
    },
    {
      selector: 'edge.rel-selected',
      style: {
        width: 4,
        'line-color': '#7aa2ff',
        'target-arrow-color': '#7aa2ff',
        color: '#e8eefc',
        'text-background-color': '#132348',
      },
    },
  ],
  layout: { name: 'cose', animate: false },
});

function showNodeDetails(node) {
  const data = node.data();
  ui.details.textContent = pretty({
    type: 'node',
    display_name: data.display_name || data.label,
    name: data.full_name || data.label,
    ...data,
  });
}

function getSelectedTypeIds() {
  return Array.from(cy.nodes(':selected')).map((n) => n.id());
}

function renderInstanceResults(payload) {
  if (!payload.error) {
    ui.instanceQuery.value = payload.query || 'No query generated.';
    ui.instanceQuery.setAttribute('readonly', 'readonly');
    ui.instanceQuery.classList.remove('edited');
  }
  const note = payload.note ? ` · ${payload.note}` : '';
  ui.instanceMeta.textContent = `Scope: ${payload.scope} · limit=${payload.limit}${note}`;
  ui.instanceQuery.classList.toggle('error', false);
  ui.instanceResults.classList.toggle('error', Boolean(payload.error));

  if (!payload.columns?.length) {
    ui.instanceResults.textContent = payload.error ? payload.error : 'No results.';
    return;
  }

  const headerCells = payload.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join('');
  const rows = payload.rows
    .map(
      (row) =>
        `<tr>${row
          .map((cell) => `<td>${escapeHtml(cell ?? '')}</td>`)
          .join('')}</tr>`,
    )
    .join('');

  ui.instanceResults.innerHTML = `
    <table class="resultTable">
      <thead><tr>${headerCells}</tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function currentScopePayload() {
  const text = ui.instanceInput.value.trim();
  const selectedTypes = ui.instanceScope.checked ? getSelectedTypeIds() : [];
  const scope = ui.instanceScope.checked ? 'selected' : 'all';
  const queryMode = getQueryMode();
  return { text, selectedTypes, scope, queryMode };
}


function getQueryMode() {
  const checked = document.querySelector('input[name="instanceQueryMode"]:checked');
  if (!checked) {
    throw new Error('Missing query mode selector');
  }
  const value = checked.value;
  if (value !== 'sql' && value !== 'pgql') {
    throw new Error(`Invalid query mode: ${value}`);
  }
  return value;
}

function showEdgeDetails(edge) {
  debug('showEdgeDetails()', { edgeId: edge.id() });
  const data = edge.data();
  ui.details.textContent = pretty({
    type: 'edge',
    display_name: data.display_name || data.type,
    name: data.full_name || data.type,
    ...data,
  });
}

let isNavigating = false;
let lastTapNodeId = null;
let lastTapAtMs = 0;
const DOUBLE_TAP_MS = 350;

// Use tapstart so clicking edge labels reliably updates details.
cy.on('tapstart', 'node', (evt) => {
  cy.elements().unselect();
  evt.target.select();
  showNodeDetails(evt.target);
  if (typeof evt.target.id === 'function') {
    const typeId = evt.target.id();
    debug('node tapstart', { typeId });
    updateRelationshipPanelFromGraph(typeId);

    const now = Date.now();
    const isDoubleTap =
      lastTapNodeId === typeId && now - lastTapAtMs <= DOUBLE_TAP_MS;
    lastTapNodeId = typeId;
    lastTapAtMs = now;

    const navMode = ui.navMode?.value || 'replace';
    if (isDoubleTap && navMode === 'replace' && !isNavigating) {
      isNavigating = true;
      debug('navigate expand (double-tap)', { typeId });
      loadVertex(typeId)
        .catch((err) => setStatus(`Error: ${err.message}`))
        .finally(() => {
          isNavigating = false;
        });
      return;
    }

    // If user hasn't taken action for this type yet, show all its incident edges
    // (within the currently loaded view).
    if (!touchedTypes.has(typeId)) {
      debug('auto-reset visibility (untouched)', { typeId });
      hiddenEdgesByFocus.set(typeId, new Set());
      focusedTypeId = typeId;
      applyVisibilityForFocusedType();
    }
  }
});

cy.on('tapstart', 'edge', (evt) => {
  cy.elements().unselect();
  evt.target.select();
  if (!hasAnyRelSelections()) {
    showEdgeDetails(evt.target);
  }
  debug('edge tapstart', { edgeId: evt.target.id() });
});

cy.on('mouseover', 'node, edge', (evt) => {
  const data = evt.target.data();
  const tooltipText = data.full_name || data.tooltip || data.label || data.type;
  const { x, y } = evt.originalEvent;
  showTooltip(tooltipText, x, y);
});

cy.on('mouseout', 'node, edge', hideTooltip);

cy.on('mousemove', (evt) => {
  if (tooltipEl.classList.contains('hidden')) return;
  const { x, y } = evt.originalEvent;
  showTooltip(tooltipEl.textContent, x, y);
});

cy.on('select', 'node', (evt) => showNodeDetails(evt.target));
cy.on('select', 'edge', (evt) => {
  if (!hasAnyRelSelections()) {
    showEdgeDetails(evt.target);
  }
});

function renderNeighborhood(payload) {
  const elements = [];

  for (const n of payload.nodes) {
    elements.push({
      group: 'nodes',
      data: {
        id: n.id,
        label: n.label,
        display_name: n.display_name || n.label,
        full_name: n.full_name || n.label,
        kind: n.kind,
        properties: n.properties,
      },
      tooltip: n.full_name || n.label,
      classes: n.id === payload.center_id ? 'center' : '',
    });
  }

  for (const e of payload.edges) {
    elements.push({
      group: 'edges',
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
        display_name: e.display_name || e.type,
        full_name: e.full_name || e.type,
        properties: e.properties,
      },
      tooltip: e.full_name || e.type,
    });
  }

  // Ensure Cytoscape element ids are set to our stable ids (not auto-generated).
  const normalized = elements.map((el) => ({
    ...el,
    data: { ...el.data, id: el.data.id },
  }));

  // Merge: add only elements that don't already exist.
  const toAdd = [];
  for (const el of normalized) {
    const id = el.data.id;
    const exists = el.group === 'nodes'
      ? cy.$(`node#${CSS.escape(id)}`)
      : cy.$(`edge#${CSS.escape(id)}`);
    if (exists.length) {
      // Update label/properties if present.
      exists.data({ ...exists.data(), ...el.data });
      if (el.classes) exists.removeClass('center').addClass(el.classes);
      continue;
    }
    toAdd.push({
      ...el,
      data: { ...el.data },
    });
  }
  if (toAdd.length) cy.add(toAdd);

  // Maintain a single focused center styling.
  cy.nodes().removeClass('center');
  const center = cy.$(`node#${CSS.escape(payload.center_id)}`);
  if (center.length) center.addClass('center');

  if (toAdd.length && ui.autoLayout?.checked) {
    runLayout();
  }

  debug('renderNeighborhood', {
    center_id: payload.center_id,
    nodes: payload.nodes?.length,
    edges: payload.edges?.length,
  });

  // Re-apply any local per-type hidden edge state.
  applyVisibilityForFocusedType();

  const moreIn = payload.has_more_in ? 'more_in' : '';
  const moreOut = payload.has_more_out ? 'more_out' : '';
  setStatus(
    `center=${payload.center_id} nodes=${payload.nodes.length} edges=${payload.edges.length} ${moreIn} ${moreOut}`.trim(),
  );
}

function runLayout() {
  const name = ui.layoutMode?.value || 'cose';
  cy.layout({ name, animate: false }).run();
  cy.fit(undefined, 30);
}

async function loadVertex(vertexId) {
  setStatus('Loading neighborhood…');

  const payload = await apiGet(`/api/type/${encodeURIComponent(vertexId)}`);
  focusedTypeId = vertexId;
  renderNeighborhood(payload);
  rememberRecent(vertexId, payload);
  updateRelationshipPanel(vertexId, payload);
}

const recentItems = [];
const RECENT_LIMIT = 8;

function rememberRecent(typeId, payload) {
  const label =
    payload?.nodes?.find((n) => n.id === typeId)?.display_name ||
    payload?.nodes?.find((n) => n.id === typeId)?.label ||
    typeId;
  const fullName = payload?.nodes?.find((n) => n.id === typeId)?.label || typeId;
  const existingIdx = recentItems.findIndex((x) => x.id === typeId);
  if (existingIdx >= 0) recentItems.splice(existingIdx, 1);
  recentItems.unshift({ id: typeId, label, fullName });
  if (recentItems.length > RECENT_LIMIT) recentItems.length = RECENT_LIMIT;
  renderRecent();
}

function renderRecent() {
  ui.recent.innerHTML = '';
  if (!recentItems.length) {
    const li = document.createElement('li');
    li.style.cursor = 'default';
    li.innerHTML = '<div class="meta">No recent selections yet.</div>';
    ui.recent.appendChild(li);
    return;
  }
  for (const r of recentItems) {
    const li = document.createElement('li');
    li.innerHTML = `
      <div class="label">${r.label}</div>
      <div class="meta">${r.fullName || r.id}</div>
    `;
    li.addEventListener('click', () => loadVertex(r.id));
    ui.recent.appendChild(li);
  }
}

let referenceCache = null;
let activeRefTab = 'vertex';

function openReferenceModal() {
  ui.modalBackdrop.classList.remove('hidden');
  ui.referenceModal.classList.remove('hidden');
  ui.refFilter.value = '';
  ui.refFilter.focus();
  renderReferenceList();
}

function closeReferenceModal() {
  ui.modalBackdrop.classList.add('hidden');
  ui.referenceModal.classList.add('hidden');
}

function setRefTab(tab) {
  activeRefTab = tab;
  ui.tabVertex.classList.toggle('active', tab === 'vertex');
  ui.tabEdge.classList.toggle('active', tab === 'edge');
  renderReferenceList();
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderReferenceList() {
  if (!referenceCache) {
    ui.refList.innerHTML = '<div class="refItem"><div>Loading…</div><div></div></div>';
    return;
  }

  const q = ui.refFilter.value.trim().toLowerCase();
  const items =
    activeRefTab === 'vertex'
      ? referenceCache.vertex_types
      : referenceCache.edge_types;

  const filtered = q
    ? items.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          (t.display_name || '').toLowerCase().includes(q),
      )
    : items;

  const capped = filtered.slice(0, 500);
  if (!capped.length) {
    ui.refList.innerHTML = '<div class="refItem"><div>No matches</div><div></div></div>';
    return;
  }

  ui.refList.innerHTML = capped
    .map((t) => {
      const meta =
        activeRefTab === 'vertex'
          ? `${t.property_count} properties`
          : 'edge label';
      return `
        <div class="refItem" data-id="${escapeHtml(t.id)}">
          <div>
            <div class="acLabel">${escapeHtml(t.display_name || t.name)}</div>
            <div class="refMeta">${escapeHtml(meta)} · ${escapeHtml(t.name)}</div>
          </div>
          <div class="refMeta">Open</div>
        </div>
      `;
    })
    .join('');
}

async function ensureReferenceLoaded() {
  if (referenceCache) return;
  referenceCache = await apiGet('/api/reference');
}

let activeSuggestions = [];
let activeSuggestionIndex = -1;
let debounceTimer = null;

function badgeForKind(kind) {
  if (kind === 'VertexType') return 'V';
  if (kind === 'EdgeType') return 'E';
  return '?';
}

function closeAutocomplete() {
  activeSuggestions = [];
  activeSuggestionIndex = -1;
  ui.autocomplete.classList.add('hidden');
  ui.autocomplete.innerHTML = '';
}

function renderAutocomplete(items) {
  if (!items.length) {
    closeAutocomplete();
    return;
  }

  ui.autocomplete.innerHTML = '';
  ui.autocomplete.classList.remove('hidden');

  for (let i = 0; i < items.length; i++) {
    const r = items[i];
    const div = document.createElement('div');
    div.className = 'acItem';
    div.dataset.index = String(i);
    div.innerHTML = `
      <div class="acBadge">${badgeForKind(r.kind)}</div>
      <div class="acMain">
        <div class="acLabel">${r.display_name || r.label}</div>
        <div class="acMeta">${r.kind || ''} · ${r.label}</div>
      </div>
    `;
    div.addEventListener('mousedown', (e) => {
      // Prevent input blur before click handler.
      e.preventDefault();
      chooseSuggestion(i);
    });
    ui.autocomplete.appendChild(div);
  }
}

function setActiveSuggestion(idx) {
  activeSuggestionIndex = idx;
  const children = Array.from(ui.autocomplete.querySelectorAll('.acItem'));
  for (const el of children) el.classList.remove('active');
  if (idx >= 0 && idx < children.length) {
    children[idx].classList.add('active');
    children[idx].scrollIntoView({ block: 'nearest' });
  }
}

async function refreshSuggestions(query) {
  const q = query.trim();
  if (q.length < 2) {
    closeAutocomplete();
    return;
  }

  try {
    const payload = await apiGet(`/api/search?q=${encodeURIComponent(q)}&limit=10`);
    activeSuggestions = payload.results || [];
    setActiveSuggestion(-1);
    renderAutocomplete(activeSuggestions);
  } catch (err) {
    closeAutocomplete();
  }
}

function scheduleSuggestions(query) {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => refreshSuggestions(query), 200);
}

function chooseSuggestion(index) {
  const r = activeSuggestions[index];
  if (!r) return;
  ui.searchInput.value = r.label;
  closeAutocomplete();
  loadVertex(r.id).catch((err) => setStatus(`Error: ${err.message}`));
}

async function doSearch(q) {
  setStatus('Searching…');
  const payload = await apiGet(`/api/search?q=${encodeURIComponent(q)}&limit=10`);

  if (!payload.results.length) {
    setStatus('No results');
    return;
  }

  // Prefer direct navigation: if exact match, open it; otherwise open first.
  const qLower = q.trim().toLowerCase();
  const exact = payload.results.find(
    (r) => (r.label || '').toLowerCase() === qLower || (r.display_name || '').toLowerCase() === qLower,
  );
  const chosen = exact || payload.results[0];
  setStatus(`Opening: ${chosen.display_name || chosen.label}`);
  await loadVertex(chosen.id);
}

ui.searchForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = ui.searchInput.value.trim();
  if (!q) return;
  doSearch(q).catch((err) => setStatus(`Error: ${err.message}`));
});

function generateInstanceQuery() {
  const { text, selectedTypes, scope, queryMode } = currentScopePayload();
  if (!text) {
    ui.instanceMeta.textContent = 'Enter a prompt to generate a query.';
    return;
  }
  ui.instanceMeta.textContent = '';
  ui.instanceQuery.classList.remove('error');
  ui.instanceQuery.value = 'Generating query…';
  ui.instanceResults.textContent = 'No results yet.';
  const payload = {
    text,
    scope,
    selected_types: selectedTypes,
    execute: false,
    query_mode: queryMode,
  };
  apiPost('/api/instance-query', payload)
    .then(renderInstanceResults)
    .catch((err) => {
      ui.instanceMeta.textContent = '';
      ui.instanceQuery.classList.add('error');
      ui.instanceQuery.value = err.message;
    });
}

ui.instanceGenerate?.addEventListener('click', generateInstanceQuery);
ui.instanceForm?.addEventListener('submit', (e) => {
  e.preventDefault();
  generateInstanceQuery();
});

ui.instanceRun?.addEventListener('click', () => {
  const { text, selectedTypes, scope, queryMode } = currentScopePayload();
  const sql = ui.instanceQuery.value.trim();
  if (!sql || sql.startsWith('Waiting for') || sql.startsWith('No query')) {
    ui.instanceMeta.textContent = 'Generate a query first.';
    return;
  }
  ui.instanceMeta.textContent = '';
  ui.instanceQuery.classList.remove('error');
  ui.instanceResults.classList.remove('error');
  ui.instanceResults.textContent = 'Running query…';
  const payload = {
    text,
    scope,
    selected_types: selectedTypes,
    execute: true,
    sql,
    query_mode: queryMode,
  };
  apiPost('/api/instance-query', payload)
    .then(renderInstanceResults)
    .catch((err) => {
      ui.instanceMeta.textContent = '';
      ui.instanceResults.classList.add('error');
      ui.instanceResults.textContent = `Error: ${err.message}`;
    });
});

ui.instanceEdit?.addEventListener('click', () => {
  ui.instanceQuery.removeAttribute('readonly');
  ui.instanceQuery.classList.add('edited');
  ui.instanceQuery.focus();
});

ui.searchInput.addEventListener('input', (e) => {
  scheduleSuggestions(e.target.value);
});

ui.searchInput.addEventListener('keydown', (e) => {
  if (ui.autocomplete.classList.contains('hidden')) return;

  if (e.key === 'Escape') {
    closeAutocomplete();
    return;
  }

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    const next = Math.min(activeSuggestions.length - 1, activeSuggestionIndex + 1);
    setActiveSuggestion(next);
    return;
  }

  if (e.key === 'ArrowUp') {
    e.preventDefault();
    const next = Math.max(-1, activeSuggestionIndex - 1);
    setActiveSuggestion(next);
    return;
  }

  if (e.key === 'Enter' && activeSuggestionIndex >= 0) {
    e.preventDefault();
    chooseSuggestion(activeSuggestionIndex);
  }
});

document.addEventListener('click', (e) => {
  if (e.target === ui.searchInput || ui.autocomplete.contains(e.target)) return;
  closeAutocomplete();
});

ui.referenceBtn.addEventListener('click', () => {
  ensureReferenceLoaded()
    .then(openReferenceModal)
    .catch((err) => setStatus(`Error: ${err.message}`));
});

ui.modalBackdrop.addEventListener('click', closeReferenceModal);
ui.modalClose.addEventListener('click', closeReferenceModal);

ui.tabVertex.addEventListener('click', () => setRefTab('vertex'));
ui.tabEdge.addEventListener('click', () => setRefTab('edge'));

ui.refFilter.addEventListener('input', renderReferenceList);

ui.refList.addEventListener('click', (e) => {
  const item = e.target.closest('.refItem');
  if (!item) return;
  const id = item.dataset.id;
  if (!id) return;
  closeReferenceModal();
  loadVertex(id).catch((err) => setStatus(`Error: ${err.message}`));
});

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (!ui.referenceModal.classList.contains('hidden')) {
    closeReferenceModal();
  }
});

let focusedTypeId = null;
let focusedNeighborhood = null;
const selectedRelEdgeIds = new Set();
// Global prune model:
// - Track which focused node hid which edges (for local reset).
// - Derive a global hidden set as the union (prune stays pruned across focus changes).
const hiddenEdgesByFocus = new Map();
const touchedTypes = new Set();

function clearAllKeepHideState() {
  hiddenEdgesByFocus.clear();
  touchedTypes.clear();
  // Clear relationship selection highlight too.
  clearRelationshipSelection();
  // Re-apply for current focus (shows everything).
  applyVisibilityForFocusedType();
  setStatus('Cleared keep/hide state');
}

function updateRelationshipPanelBase(typeId, nodeLabel, edges) {
  if (!typeId) return;
  focusedTypeId = typeId;
  clearRelationshipSelection();

  const fullName =
    focusedNeighborhood?.nodes?.find((n) => n.id === typeId)?.label || typeId;
  ui.relNote.textContent = `For: ${nodeLabel} (${fullName})`;
  const outEdges = edges.filter((e) => e.source === typeId);
  const inEdges = edges.filter((e) => e.target === typeId);
  renderRelList(ui.relOut, outEdges, { direction: 'out' });
  renderRelList(ui.relIn, inEdges, { direction: 'in' });
}

function updateRelationshipPanel(typeId, payload) {
  focusedNeighborhood = payload;
  const nodeLabel =
    payload?.nodes?.find((n) => n.id === typeId)?.display_name ||
    payload?.nodes?.find((n) => n.id === typeId)?.label ||
    typeId;
  updateRelationshipPanelBase(typeId, nodeLabel, payload?.edges || []);
}

function updateRelationshipPanelFromGraph(typeId) {
  if (!typeId) return;
  const node = cy.$(`node#${CSS.escape(typeId)}`);
  const nodeLabel = node.length ? node.data('display_name') || node.data('label') : typeId;
  const incident = cy
    .edges()
    .filter((e) => e.data('source') === typeId || e.data('target') === typeId)
    .map((e) => ({
      id: e.id(),
      source: e.data('source'),
      target: e.data('target'),
      type: e.data('type'),
    }));

  // Populate neighbor labels from the current graph.
  focusedNeighborhood = {
    nodes: cy
      .nodes()
      .map((n) => ({
        id: n.id(),
        label: n.data('label') || n.id(),
        display_name: n.data('display_name') || n.data('label') || n.id(),
      })),
    edges: [],
  };
  updateRelationshipPanelBase(typeId, nodeLabel, incident);

  // Re-apply any local hide/keep state for this focused type.
  applyVisibilityForFocusedType();
}

function nodeLabelById(payload, id) {
  return (
    payload?.nodes?.find((n) => n.id === id)?.display_name ||
    payload?.nodes?.find((n) => n.id === id)?.label ||
    id
  );
}

function renderRelList(container, edges, { direction }) {
  if (!focusedNeighborhood) {
    container.innerHTML = '';
    return;
  }

  if (!edges.length) {
    container.innerHTML = '<div class="relRow"><div></div><div class="relSub">(none)</div></div>';
    return;
  }

  container.innerHTML = edges
    .map((e) => {
      const neighborId = direction === 'out' ? e.target : e.source;
      const neighborLabel = nodeLabelById(focusedNeighborhood, neighborId);
      const edgeName = e.display_name || e.type;
      const title =
        direction === 'out'
          ? `${edgeName} → ${neighborLabel}`
          : `${neighborLabel} → ${edgeName}`;

      return `
        <div class="relRow" data-edge-id="${escapeHtml(e.id)}">
          <input type="checkbox" />
          <div>
            <div class="relTitle">${escapeHtml(title)}</div>
            <div class="relSub">${escapeHtml(e.type)}</div>
          </div>
        </div>
      `;
    })
    .join('');
}

function setEdgeSelection(edgeId, selected) {
  if (selected) selectedRelEdgeIds.add(edgeId);
  else selectedRelEdgeIds.delete(edgeId);

  for (const listEl of [ui.relOut, ui.relIn]) {
    const row = listEl.querySelector(`[data-edge-id="${CSS.escape(edgeId)}"]`);
    if (!row) continue;
    row.classList.toggle('selected', selected);
    const cb = row.querySelector('input[type="checkbox"]');
    if (cb) cb.checked = selected;
  }

  const edge = cy.$(`edge#${CSS.escape(edgeId)}`);
  if (edge.length) {
    if (selected) edge.addClass('rel-selected');
    else edge.removeClass('rel-selected');
  }

  updateDetailsFromRelSelection();
  debug('rel selection', {
    edgeId,
    selected,
    count: selectedRelEdgeIds.size,
    ids: Array.from(selectedRelEdgeIds),
  });
}

function clearRelationshipSelection() {
  for (const edgeId of Array.from(selectedRelEdgeIds)) {
    const edge = cy.$(`edge#${CSS.escape(edgeId)}`);
    if (edge.length) edge.removeClass('rel-selected');
  }
  selectedRelEdgeIds.clear();

  // Also clear checkbox UI state.
  for (const listEl of [ui.relOut, ui.relIn]) {
    for (const row of listEl.querySelectorAll('.relRow.selected')) {
      row.classList.remove('selected');
      const cb = row.querySelector('input[type="checkbox"]');
      if (cb) cb.checked = false;
    }
  }
}


function edgeSummary(edgeEl) {
  const d = edgeEl.data();
  return {
    id: edgeEl.id(),
    source: d.source,
    target: d.target,
    type: d.type,
    display_name: d.display_name || d.type,
    name: d.full_name || d.type,
    properties: d.properties,
  };
}

function updateDetailsFromRelSelection() {
  // Only override details when selection is coming from the left-panel checkboxes.
  const ids = Array.from(selectedRelEdgeIds);
  if (!ids.length) return;

  const edges = ids
    .map((id) => cy.$(`edge#${CSS.escape(id)}`))
    .filter((col) => col.length)
    .map((col) => edgeSummary(col[0]));

  if (!edges.length) return;

  if (edges.length === 1) {
    ui.details.textContent = pretty({ type: 'edge', ...edges[0] });
    debug('details from rel selection (single)', { id: edges[0].id });
    return;
  }

  ui.details.textContent = pretty({
    type: 'edge_selection',
    count: edges.length,
    edges,
  });
  debug('details from rel selection (multi)', {
    count: edges.length,
    ids: edges.map((e) => e.id),
  });
}

function hasAnyRelSelections() {
  return selectedRelEdgeIds.size >= 1;
}

function applyVisibilityForFocusedType() {
  if (!focusedTypeId) return;
  // Reset visibility first.
  cy.nodes().forEach((n) => n.style('display', 'element'));
  cy.edges().forEach((e) => e.style('display', 'element'));

  // Apply global pruned edges (union across all focused nodes).
  const globallyHidden = new Set();
  for (const set of hiddenEdgesByFocus.values()) {
    for (const edgeId of set) globallyHidden.add(edgeId);
  }
  for (const edge of cy.edges()) {
    if (globallyHidden.has(edge.id())) edge.style('display', 'none');
  }

  // Hide disconnected subgraphs is always enabled for this phase.
  if (ui.hideDisconnected.checked) {
    // Compute connectivity using the *visible* graph only; otherwise hidden edges
    // can still participate in traversal and make disconnected subgraphs appear
    // connected.
    const root = cy.$(`node#${CSS.escape(focusedTypeId)}`);
    if (!root.length) return;
    root.style('display', 'element');
    const bfs = cy.elements(':visible').bfs({ roots: root });
    const connected = new Set(bfs.path.map((el) => el.id()));
    // Ensure the focused node is always considered connected.
    connected.add(focusedTypeId);
    cy.nodes().forEach((n) => {
      n.style('display', connected.has(n.id()) ? 'element' : 'none');
    });
    cy.edges().forEach((e) => {
      e.style('display', connected.has(e.id()) ? 'element' : 'none');
    });
  } else {
    // Default: optionally hide nodes that become true orphans after hiding incident edges.
    cy.nodes().forEach((n) => {
      if (n.id() === focusedTypeId) return;
      if (n.style('display') !== 'none' && n.connectedEdges(':visible').length === 0) {
        n.style('display', 'none');
      }
    });
  }
}

function ensureHiddenSet(typeId) {
  if (!hiddenEdgesByFocus.has(typeId)) hiddenEdgesByFocus.set(typeId, new Set());
  return hiddenEdgesByFocus.get(typeId);
}

function incidentEdgeIds(typeId) {
  if (!typeId) return [];
  return cy
    .edges()
    .filter((e) => e.data('source') === typeId || e.data('target') === typeId)
    .map((e) => e.id());
}

function keepSelectedForFocusedType() {
  if (!focusedTypeId) return;
  if (!focusedNeighborhood) {
    setStatus('Open a neighborhood first (double-click a node)');
    return;
  }
  if (!selectedRelEdgeIds.size) {
    setStatus('Select one or more relationships first');
    return;
  }
  touchedTypes.add(focusedTypeId);
  const hidden = ensureHiddenSet(focusedTypeId);
  const candidateEdges = incidentEdgeIds(focusedTypeId);

  debug('keepSelectedForFocusedType', {
    focusedTypeId,
    selectedCount: selectedRelEdgeIds.size,
    candidateCount: candidateEdges.length,
  });

  for (const edgeId of candidateEdges) {
    if (!selectedRelEdgeIds.has(edgeId)) hidden.add(edgeId);
  }
  applyVisibilityForFocusedType();
}

function hideSelectedForFocusedType() {
  if (!focusedTypeId) return;
  if (!selectedRelEdgeIds.size) {
    setStatus('Select one or more relationships first');
    return;
  }
  touchedTypes.add(focusedTypeId);
  const hidden = ensureHiddenSet(focusedTypeId);

  debug('hideSelectedForFocusedType', {
    focusedTypeId,
    selectedCount: selectedRelEdgeIds.size,
  });
  for (const id of selectedRelEdgeIds) hidden.add(id);
  applyVisibilityForFocusedType();
}

function resetFocusedTypeVisibility() {
  if (!focusedTypeId) return;
  touchedTypes.delete(focusedTypeId);
  hiddenEdgesByFocus.delete(focusedTypeId);
  applyVisibilityForFocusedType();
}

function attachRelListHandlers(container) {
  container.addEventListener('click', (e) => {
    const row = e.target.closest('.relRow');
    if (!row) return;
    const edgeId = row.dataset.edgeId;
    if (!edgeId) return;

    // Keep Cytoscape selection untouched when using the list.
    // Canvas clicks continue to show single-edge details.
    const nowSelected = !selectedRelEdgeIds.has(edgeId);
    setEdgeSelection(edgeId, nowSelected);
  });
}

attachRelListHandlers(ui.relOut);
attachRelListHandlers(ui.relIn);

ui.keepSelected.addEventListener('click', () => {
  if (!focusedTypeId) {
    setStatus('Select a type node first');
    return;
  }
  keepSelectedForFocusedType();
});

ui.hideSelected.addEventListener('click', () => {
  if (!focusedTypeId) {
    setStatus('Select a type node first');
    return;
  }
  hideSelectedForFocusedType();
});

ui.clearRel.addEventListener('click', () => {
  clearRelationshipSelection();
});

ui.resetType.addEventListener('click', () => {
  if (!focusedTypeId) {
    setStatus('Select a type node first');
    return;
  }
  resetFocusedTypeVisibility();
});

// hideDisconnected is pinned on, but keep this in case we re-enable it.
ui.hideDisconnected.addEventListener('change', () => {
  applyVisibilityForFocusedType();
});

ui.clearAllVisibility.addEventListener('click', () => {
  clearAllKeepHideState();
});

ui.layoutMode.addEventListener('change', () => {
  if (ui.autoLayout.checked) runLayout();
});

ui.autoLayout.addEventListener('change', () => {
  if (ui.autoLayout.checked) runLayout();
});

// Initial view
async function initActiveGraphLabel() {
  if (!ui.activeGraphName) return;
  try {
    const cfg = await apiGet('/api/config');
    ui.activeGraphName.textContent = cfg.active_graph || 'Graph';
    setSearchPlaceholder(cfg.active_graph || 'Graph');
    // Also set a helpful status line for debugging.
    if (cfg.ddl_path) setStatus(`Graph=${cfg.active_graph} (DDL: ${cfg.ddl_path})`);
  } catch {
    ui.activeGraphName.textContent = 'Graph';
    setSearchPlaceholder('Graph');
  }
}

function resetGraphStateForViewAll(centerId) {
  // Clear graph + stateful filters when switching to an entirely new view.
  cy.elements().remove();
  focusedTypeId = centerId || null;
  focusedNeighborhood = null;
  clearAllKeepHideState();
  renderRecent();
}

async function loadViewAll() {
  setStatus('Loading full graph…');
  try {
    const payload = await apiGet('/api/view-all');
    resetGraphStateForViewAll(payload.center_id);
    focusedTypeId = payload.center_id;
    renderNeighborhood(payload);
    // Ensure right panel is populated.
    updateRelationshipPanel(payload.center_id, payload);
    runLayout();
    setStatus(`Loaded full graph: nodes=${payload.nodes.length} edges=${payload.edges.length}`);
  } catch (err) {
    setStatus(`Cannot load full graph: ${err.message}`);
  }
}

async function initStartupGraph() {
  try {
    const overview = await apiGet('/api/overview');
    const canViewAll = Boolean(overview?.counts?.can_view_all);
    const preload = Boolean(overview?.preload_if_small);
    if (preload && canViewAll) {
      await loadViewAll();
      return;
    }

    if (!canViewAll) {
      setStatus(
        `Graph too big to load automatically (artifacts=${overview?.counts?.artifacts}, max=${overview?.max_artifacts}). Tip: search for a type.`,
      );
    }
  } catch {
    // ignore
  }
}

ui.viewAllBtn?.addEventListener('click', () => {
  loadViewAll();
});

initActiveGraphLabel();
setMainTab('instance');
setStatus('Tip: search for a type');
initStartupGraph();
renderRecent();
