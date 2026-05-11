/**
 * Ctrl+K Command Palette
 * ======================
 *
 * Controller vanilla JS para o modal global de busca/navegacao.
 *
 * Atalhos:
 *   Ctrl/Cmd+K        — abrir/fechar
 *   Esc               — fechar
 *   Up/Down           — navegar (loop)
 *   Enter             — abrir (mesma aba)
 *   Ctrl/Cmd+Enter    — abrir em nova aba
 *   Tab               — cicla escopo (Tudo > Comandos > Pedidos > NFs > Tudo)
 *   Backspace (vazio) — sai do escopo
 *
 * Recentes: armazenados em localStorage (max 8).
 *
 * Para impedir captura do Ctrl+K em um area especifica, adicione
 * o atributo data-no-cmdk no container.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------- constantes
  const ENDPOINT_BUSCAR    = '/api/cmdk/buscar';
  const ENDPOINT_COMANDOS  = '/api/cmdk/comandos';
  const DEBOUNCE_MS        = 220;
  const MIN_QUERY_LEN      = 2;
  const STORAGE_KEY        = 'cmdk:recents:v1';
  const MAX_RECENTS        = 8;
  const SCOPES             = ['all', 'comando', 'pedido', 'nf'];
  const SCOPE_LABELS       = {
    all:     '',
    comando: 'Comandos',
    pedido:  'Pedidos',
    nf:      'NFs',
  };

  // ---------------------------------------------------------------- estado
  const state = {
    open: false,
    items: [],         // lista plana de items renderizados (para nav)
    activeIdx: -1,
    scope: 'all',
    abort: null,
    debounceTimer: null,
    lastFocus: null,
  };

  // ---------------------------------------------------------------- elementos
  let overlay, input, listbox, scopeTag, btnClose;
  let elResults, elRecents, elNoResultsQ;
  let stateNodes = {};   // {empty, loading, 'no-results'}

  // ============================================================================
  // Init
  // ============================================================================

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    overlay = document.getElementById('cmdk-overlay');
    if (!overlay) return; // modal nao esta no DOM (ex: pagina de login)

    input        = overlay.querySelector('#cmdk-input');
    listbox      = overlay.querySelector('#cmdk-listbox');
    scopeTag     = overlay.querySelector('#cmdk-scope-tag');
    btnClose     = overlay.querySelector('[data-cmdk-close]');
    elResults    = overlay.querySelector('[data-cmdk-results]');
    elRecents    = overlay.querySelector('[data-cmdk-recents]');
    elNoResultsQ = overlay.querySelector('[data-cmdk-no-results-q]');

    overlay.querySelectorAll('[data-cmdk-state]').forEach((node) => {
      stateNodes[node.dataset.cmdkState] = node;
    });

    bindEvents();
  }

  function bindEvents() {
    // Atalho global Ctrl+K / Cmd+K
    document.addEventListener('keydown', onGlobalKeydown, { capture: true });

    // Triggers manuais (botoes em topbar/sidebar)
    document.querySelectorAll('[data-cmdk-toggle]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        open();
      });
    });

    // Click no overlay (fora do modal) fecha
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    if (btnClose) {
      btnClose.addEventListener('click', close);
    }

    // Input
    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onInputKeydown);
  }

  // ============================================================================
  // Open / Close
  // ============================================================================

  function open() {
    if (state.open) return;
    state.open = true;
    state.lastFocus = document.activeElement;

    overlay.hidden = false;
    document.body.style.overflow = 'hidden';

    input.value = '';
    state.scope = 'all';
    updateScopeTag();
    renderEmpty();

    // Foco apos paint (mobile precisa)
    requestAnimationFrame(() => {
      input.focus();
      input.select();
    });
  }

  function close() {
    if (!state.open) return;
    state.open = false;

    overlay.hidden = true;
    document.body.style.overflow = '';

    if (state.abort) {
      state.abort.abort();
      state.abort = null;
    }
    if (state.debounceTimer) {
      clearTimeout(state.debounceTimer);
      state.debounceTimer = null;
    }

    // Restaura foco
    if (state.lastFocus && state.lastFocus.focus) {
      try { state.lastFocus.focus(); } catch (_) { /* noop */ }
    }
    state.lastFocus = null;
    state.items = [];
    state.activeIdx = -1;
  }

  function toggle() {
    if (state.open) close(); else open();
  }

  // ============================================================================
  // Keydown handlers
  // ============================================================================

  function onGlobalKeydown(e) {
    // Ctrl+K / Cmd+K
    const isK = (e.key === 'k' || e.key === 'K');
    if (isK && (e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey) {
      // Respeita opt-out
      const tgt = e.target;
      if (tgt && tgt.closest && tgt.closest('[data-no-cmdk]')) return;
      e.preventDefault();
      e.stopPropagation();
      toggle();
      return;
    }

    // Esc fecha (apenas quando aberto)
    if (state.open && e.key === 'Escape') {
      e.preventDefault();
      close();
    }
  }

  function onInputKeydown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      moveActive(+1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      moveActive(-1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      activateCurrent(e.ctrlKey || e.metaKey);
    } else if (e.key === 'Tab') {
      e.preventDefault();
      cycleScope(e.shiftKey ? -1 : +1);
    } else if (e.key === 'Backspace' && input.value === '' && state.scope !== 'all') {
      e.preventDefault();
      state.scope = 'all';
      updateScopeTag();
      runSearch('');
    }
  }

  // ============================================================================
  // Search (debounced + AbortController)
  // ============================================================================

  function onInput() {
    if (state.debounceTimer) clearTimeout(state.debounceTimer);
    const q = input.value;
    state.debounceTimer = setTimeout(() => runSearch(q), DEBOUNCE_MS);
  }

  function runSearch(q) {
    q = (q || '').trim();
    if (q.length < MIN_QUERY_LEN) {
      renderEmpty();
      return;
    }
    showState('loading');

    if (state.abort) state.abort.abort();
    state.abort = new AbortController();

    const params = new URLSearchParams({ q: q, tipo: state.scope, limit: '6' });
    fetch(`${ENDPOINT_BUSCAR}?${params}`, {
      signal: state.abort.signal,
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    })
      .then((r) => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
      .then((data) => {
        if (!data.success) {
          showState('no-results');
          return;
        }
        renderGroups(data.groups || [], q);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        console.error('[cmdk] busca falhou:', err);
        showState('no-results');
      });
  }

  // ============================================================================
  // Render
  // ============================================================================

  function renderEmpty() {
    state.items = [];
    state.activeIdx = -1;
    elResults.innerHTML = '';
    renderRecents();
    showState('empty');
  }

  function showState(name) {
    elResults.hidden = (name !== 'results');
    Object.entries(stateNodes).forEach(([key, node]) => {
      node.hidden = (key !== name);
    });
    if (name === 'results') {
      elResults.hidden = false;
      Object.values(stateNodes).forEach((n) => { n.hidden = true; });
    }
  }

  function renderGroups(groups, q) {
    state.items = [];
    state.activeIdx = -1;

    if (!groups || !groups.length) {
      if (elNoResultsQ) elNoResultsQ.textContent = q;
      showState('no-results');
      return;
    }

    const html = groups.map((group) => renderGroup(group)).join('');
    elResults.innerHTML = html;
    showState('results');

    // Coleta items renderizados em ordem (para keyboard nav)
    state.items = Array.from(elResults.querySelectorAll('.cmdk-item'));
    if (state.items.length) {
      setActive(0);
    }

    // Wire click handlers
    state.items.forEach((node, idx) => {
      node.addEventListener('click', (e) => {
        setActive(idx);
        activateCurrent(e.ctrlKey || e.metaKey);
      });
      node.addEventListener('mousemove', () => {
        if (state.activeIdx !== idx) setActive(idx, /*scroll=*/ false);
      });
    });
  }

  function renderGroup(group) {
    const itemsHtml = group.items.map((item) => renderItem(item)).join('');
    return (
      `<div class="cmdk-group">
        <div class="cmdk-group-header">
          <i class="${esc(group.icon || 'fas fa-circle')}" aria-hidden="true"></i>
          <span>${esc(group.label)}</span>
        </div>
        ${itemsHtml}
      </div>`
    );
  }

  function renderItem(item) {
    const badgeHtml = item.badge
      ? `<span class="cmdk-item__badge cmdk-item__badge--${esc(item.badge.tone || 'secondary')}">${esc(item.badge.label)}</span>`
      : '';
    return (
      `<div class="cmdk-item"
            role="option"
            data-url="${esc(item.url)}"
            data-tipo="${esc(item.tipo || 'comando')}"
            data-id="${esc(item.id)}"
            data-label="${esc(item.label)}">
        <span class="cmdk-item__icon">
          <i class="${esc(item.icon || 'fas fa-circle')}" aria-hidden="true"></i>
        </span>
        <div class="cmdk-item__main">
          <div class="cmdk-item__label">${esc(item.label)}</div>
          ${item.subtitle ? `<div class="cmdk-item__subtitle">${esc(item.subtitle)}</div>` : ''}
        </div>
        ${badgeHtml}
        <span class="cmdk-item__shortcut">↵</span>
      </div>`
    );
  }

  // ============================================================================
  // Recents (localStorage)
  // ============================================================================

  function renderRecents() {
    const recents = readRecents();
    if (!recents.length) {
      elRecents.innerHTML = '';
      return;
    }
    elRecents.innerHTML = recents.map((it) => renderItem(it)).join('');

    // Wire clicks
    elRecents.querySelectorAll('.cmdk-item').forEach((node, idx) => {
      node.addEventListener('click', (e) => {
        const item = recents[idx];
        if (item) navigate(item, e.ctrlKey || e.metaKey);
      });
    });
  }

  function readRecents() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const arr = JSON.parse(raw);
      return Array.isArray(arr) ? arr.slice(0, MAX_RECENTS) : [];
    } catch (_) {
      return [];
    }
  }

  function pushRecent(item) {
    if (!item) return;
    let recents = readRecents();
    // Remove duplicata
    recents = recents.filter((r) => !(r.tipo === item.tipo && r.id === item.id));
    recents.unshift({
      tipo:     item.tipo,
      id:       item.id,
      label:    item.label,
      subtitle: item.subtitle || '',
      url:      item.url,
      icon:     item.icon || 'fas fa-circle',
      badge:    item.badge || null,
    });
    recents = recents.slice(0, MAX_RECENTS);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(recents)); }
    catch (_) { /* quota exceeded — ignora */ }
  }

  // ============================================================================
  // Navigation / activation
  // ============================================================================

  function moveActive(delta) {
    if (!state.items.length) return;
    let next = state.activeIdx + delta;
    if (next < 0) next = state.items.length - 1;
    if (next >= state.items.length) next = 0;
    setActive(next);
  }

  function setActive(idx, scroll) {
    state.items.forEach((node, i) => {
      node.classList.toggle('cmdk-item--active', i === idx);
    });
    state.activeIdx = idx;

    const node = state.items[idx];
    if (node) {
      input.setAttribute('aria-activedescendant', node.id || '');
      if (scroll !== false) {
        node.scrollIntoView({ block: 'nearest', behavior: 'instant' });
      }
    }
  }

  function activateCurrent(newTab) {
    const node = state.items[state.activeIdx];
    if (!node) return;
    const item = {
      tipo:     node.dataset.tipo,
      id:       node.dataset.id,
      label:    node.dataset.label,
      subtitle: node.querySelector('.cmdk-item__subtitle')?.textContent || '',
      url:      node.dataset.url,
      icon:     node.querySelector('.cmdk-item__icon i')?.className || 'fas fa-circle',
    };
    navigate(item, newTab);
  }

  function navigate(item, newTab) {
    if (!item || !item.url) return;
    pushRecent(item);
    if (newTab) {
      window.open(item.url, '_blank', 'noopener');
    } else {
      window.location.href = item.url;
    }
    close();
  }

  // ============================================================================
  // Scope cycling
  // ============================================================================

  function cycleScope(delta) {
    const idx = SCOPES.indexOf(state.scope);
    let next = idx + delta;
    if (next < 0) next = SCOPES.length - 1;
    if (next >= SCOPES.length) next = 0;
    state.scope = SCOPES[next];
    updateScopeTag();
    runSearch(input.value);
  }

  function updateScopeTag() {
    const label = SCOPE_LABELS[state.scope];
    if (!label) {
      scopeTag.hidden = true;
      scopeTag.textContent = '';
    } else {
      scopeTag.hidden = false;
      scopeTag.textContent = label;
    }
  }

  // ============================================================================
  // Util
  // ============================================================================

  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Expor no escopo global para debugging (opcional)
  window.cmdk = { open, close, toggle };
})();
