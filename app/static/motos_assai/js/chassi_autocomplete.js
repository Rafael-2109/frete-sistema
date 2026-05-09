/**
 * Autocomplete de chassi para inputs operacionais do modulo Motos Assai.
 *
 * Atrela-se a qualquer <input data-chassi-autocomplete='{"contexto":"...", "reciboId":N}'>
 * Dispara busca somente quando o input tem >= 4 chars (debounce 220ms).
 * Backend: GET /motos-assai/api/chassi/autocomplete?q=&contexto=&recibo_id=
 *
 * Comportamento ao selecionar item: PREENCHE o input + foca, sem submeter.
 * Mantem compatibilidade com leitores USB/QR (Enter so e interceptado quando
 * o dropdown esta aberto e ha um item destacado).
 *
 * Layout das opcoes:
 *   Desktop (>=md): {chassi} - {modelo_codigo} - {cor}
 *   Mobile  (<md):  {chassi}
 *                   {modelo_codigo} - {cor}
 */
(function () {
  'use strict';

  var ENDPOINT = '/motos-assai/api/chassi/autocomplete';
  var MIN_CHARS = 4;
  var DEBOUNCE_MS = 220;
  var STYLE_ID = 'ma-chassi-autocomplete-style';

  function injectStylesOnce() {
    if (document.getElementById(STYLE_ID)) return;
    var css = ''
      // top:100% + left:0 ancora o dropdown ABAIXO do parent (.input-group),
      // evitando sobrepor irmaos como o btn-camera. Sem essas coordenadas o
      // navegador calcula static position em flex-wrap, alinhando o dropdown
      // com o TOPO do parent — o que cobre o botao da camera ao lado do input.
      + '.ma-chassi-suggest{position:absolute;top:100%;left:0;z-index:1080;display:none;'
      + 'pointer-events:none;'
      + 'min-width:100%;max-width:480px;max-height:280px;overflow-y:auto;'
      + 'background:var(--bs-body-bg,#fff);border:1px solid var(--bs-border-color,#dee2e6);'
      + 'border-radius:.375rem;box-shadow:0 .5rem 1rem rgba(0,0,0,.15);margin-top:2px;}'
      + '.ma-chassi-suggest.is-open{display:block;pointer-events:auto;}'
      + '.ma-chassi-suggest__item{padding:.5rem .75rem;cursor:pointer;border-bottom:1px solid var(--bs-border-color,#eee);font-size:.95rem;line-height:1.3;}'
      + '.ma-chassi-suggest__item:last-child{border-bottom:none;}'
      + '.ma-chassi-suggest__item:hover,.ma-chassi-suggest__item.is-active{background:var(--bs-tertiary-bg,#f1f3f5);}'
      + '.ma-chassi-suggest__chassi{font-family:var(--bs-font-monospace,monospace);font-weight:600;}'
      + '.ma-chassi-suggest__meta{color:var(--bs-secondary-color,#6c757d);}'
      + '.ma-chassi-suggest__empty{padding:.5rem .75rem;color:var(--bs-secondary-color,#6c757d);font-size:.875rem;font-style:italic;}'
      // Mobile: meta na 2a linha; separador some
      + '@media (max-width:767.98px){'
      + '.ma-chassi-suggest{max-width:100%;}'
      + '.ma-chassi-suggest__sep{display:none;}'
      + '.ma-chassi-suggest__meta{display:block;font-size:.85rem;}'
      + '}';
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.appendChild(document.createTextNode(css));
    document.head.appendChild(style);
  }

  function getCsrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute('content') : '';
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function debounce(fn, wait) {
    var t = null;
    return function () {
      var ctx = this, args = arguments;
      if (t) clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  }

  function parseConfig(input) {
    var raw = input.getAttribute('data-chassi-autocomplete');
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      console.warn('[chassi-autocomplete] config invalida em', input, raw);
      return null;
    }
  }

  function buildUrl(cfg, q) {
    var params = new URLSearchParams();
    params.set('q', q);
    params.set('contexto', cfg.contexto);
    if (cfg.reciboId != null) params.set('recibo_id', String(cfg.reciboId));
    if (cfg.limit != null) params.set('limit', String(cfg.limit));
    return ENDPOINT + '?' + params.toString();
  }

  function attach(input) {
    var cfg = parseConfig(input);
    if (!cfg || !cfg.contexto) return;
    if (input.dataset.chassiAutocompleteAttached === '1') return;
    input.dataset.chassiAutocompleteAttached = '1';

    // Container: posicionamento relativo no parent
    var parent = input.parentElement;
    if (parent && getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }

    var dropdown = document.createElement('div');
    dropdown.className = 'ma-chassi-suggest';
    dropdown.setAttribute('role', 'listbox');
    parent.appendChild(dropdown);

    var state = {
      items: [],
      activeIdx: -1,
      lastQuery: '',
      requestSeq: 0,
      open: false,
    };

    function close() {
      state.open = false;
      state.activeIdx = -1;
      dropdown.classList.remove('is-open');
      dropdown.innerHTML = '';
    }

    function open() {
      state.open = true;
      dropdown.classList.add('is-open');
    }

    function render() {
      if (!state.items.length) {
        dropdown.innerHTML = '<div class="ma-chassi-suggest__empty">Nenhum chassi encontrado.</div>';
        open();
        return;
      }
      var html = '';
      for (var i = 0; i < state.items.length; i++) {
        var it = state.items[i];
        var meta = [it.modelo_codigo || '', it.cor || ''].filter(Boolean).join(' - ');
        var activeCls = i === state.activeIdx ? ' is-active' : '';
        html += ''
          + '<div class="ma-chassi-suggest__item' + activeCls + '" role="option" data-idx="' + i + '">'
          +   '<span class="ma-chassi-suggest__chassi">' + escapeHtml(it.chassi) + '</span>'
          +   (meta ? '<span class="ma-chassi-suggest__sep"> - </span>'
          +           '<span class="ma-chassi-suggest__meta">' + escapeHtml(meta) + '</span>' : '')
          + '</div>';
      }
      dropdown.innerHTML = html;
      open();
    }

    function setActive(idx) {
      state.activeIdx = idx;
      var nodes = dropdown.querySelectorAll('.ma-chassi-suggest__item');
      for (var i = 0; i < nodes.length; i++) {
        nodes[i].classList.toggle('is-active', i === idx);
      }
      var active = nodes[idx];
      if (active && active.scrollIntoView) {
        active.scrollIntoView({block: 'nearest'});
      }
    }

    function selectIdx(idx) {
      var it = state.items[idx];
      if (!it) return;
      input.value = it.chassi;
      close();
      input.focus();
    }

    var doFetch = debounce(function (q) {
      var seq = ++state.requestSeq;
      fetch(buildUrl(cfg, q), {
        credentials: 'same-origin',
        headers: {'Accept': 'application/json', 'X-CSRFToken': getCsrfToken()},
      })
        .then(function (r) { return r.ok ? r.json() : {ok: false, items: []}; })
        .then(function (data) {
          // Descarta respostas obsoletas
          if (seq !== state.requestSeq) return;
          state.items = (data && data.items) || [];
          // activeIdx = -1 (nada pre-selecionado): Enter passa para o handler
          // de submit do leitor USB. Usuario navega com seta para escolher item.
          state.activeIdx = -1;
          render();
        })
        .catch(function () {
          if (seq !== state.requestSeq) return;
          close();
        });
    }, DEBOUNCE_MS);

    input.addEventListener('input', function () {
      var q = (input.value || '').trim();
      if (q.length < MIN_CHARS) {
        state.requestSeq++;  // invalida fetches em voo
        close();
        return;
      }
      if (q === state.lastQuery) return;
      state.lastQuery = q;
      doFetch(q);
    });

    // capture:true para interceptar Enter ANTES dos handlers existentes
    // (operacao_quick.js / separacao_chassi.js / recebimento_wizard.js).
    // SO interceptamos Enter quando o usuario navegou explicitamente com
    // setas (activeIdx >= 0). Sem navegacao, Enter passa para o handler de
    // submit (leitor USB / botao validar) sem precisar de Enter duplo.
    input.addEventListener('keydown', function (e) {
      if (!state.open || !state.items.length) return;
      var n = state.items.length;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        setActive(state.activeIdx < 0 ? 0 : (state.activeIdx + 1) % n);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        setActive(state.activeIdx < 0 ? n - 1 : (state.activeIdx - 1 + n) % n);
      } else if (e.key === 'Enter') {
        if (state.activeIdx >= 0) {
          e.preventDefault();
          e.stopImmediatePropagation();
          selectIdx(state.activeIdx);
        }
      } else if (e.key === 'Escape') {
        e.stopPropagation();
        close();
      } else if (e.key === 'Tab') {
        close();
      }
    }, true);

    dropdown.addEventListener('mousedown', function (e) {
      // mousedown (nao click) para nao perder foco antes de selecionar
      var item = e.target.closest('.ma-chassi-suggest__item');
      if (!item) return;
      e.preventDefault();
      var idx = parseInt(item.getAttribute('data-idx'), 10);
      if (!Number.isNaN(idx)) selectIdx(idx);
    });

    document.addEventListener('mousedown', function (e) {
      if (!state.open) return;
      if (e.target === input || dropdown.contains(e.target)) return;
      close();
    });

    input.addEventListener('blur', function () {
      // pequeno delay para permitir mousedown no item
      setTimeout(function () {
        if (!dropdown.contains(document.activeElement)) close();
      }, 120);
    });
  }

  function init() {
    injectStylesOnce();
    var inputs = document.querySelectorAll('input[data-chassi-autocomplete]');
    inputs.forEach(attach);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exposicao opcional para reattach manual em DOM dinamico
  window.MotosAssaiChassiAutocomplete = {attach: attach, init: init};
})();
