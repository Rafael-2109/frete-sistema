/**
 * Autocomplete reutilizavel para o modulo HORA.
 *
 * Uso minimo:
 *   <input data-hora-autocomplete="chassi" name="chassi" ...>
 *
 * Atributos data-* opcionais:
 *   data-hora-autocomplete: chassi|pedido|nf-entrada|venda|cliente|loja-externa|modelo|loja
 *   data-hora-min-chars: minimo de caracteres para disparar busca (default 2)
 *   data-hora-debounce-ms: debounce em ms (default 200)
 *   data-hora-target-id: id do hidden input que recebera o valor canonico
 *                        (ex.: pedido_id, modelo_id). Se ausente, escreve no
 *                        proprio input.
 *   data-hora-target-key: chave do JSON usada como valor (default depende do
 *                         tipo: id para pedido/modelo/loja/venda; chassi para
 *                         chassi; numero_nf para nf-entrada; nome_cliente para
 *                         cliente; nome para loja-externa).
 *   data-hora-extra-params: query string adicional (ex.: "sem_recebimento=1&ativo=1").
 *                           Concatenado a "?q=...".
 *
 * O dropdown segue o input. Sem dependencias externas (vanilla JS, Bootstrap
 * apenas para classes visuais).
 */
(function() {
  'use strict';

  const ENDPOINTS = {
    'chassi':         '/hora/autocomplete/chassi',
    'pedido':         '/hora/autocomplete/pedido',
    'nf-entrada':     '/hora/autocomplete/nf-entrada',
    'venda':          '/hora/autocomplete/venda',
    'cliente':        '/hora/autocomplete/cliente',
    'loja-externa':   '/hora/autocomplete/loja-externa',
    'modelo':         '/hora/autocomplete/modelo',
    'loja':           '/hora/autocomplete/loja',
    'peca':           '/hora/autocomplete/peca',
  };

  // Chave default por tipo, usada quando o usuario nao especifica
  // data-hora-target-key.
  const DEFAULT_KEYS = {
    'chassi':       'chassi',
    'pedido':       'numero_pedido',
    'nf-entrada':   'numero_nf',
    'venda':        'nf_saida_numero',
    'cliente':      'nome_cliente',
    'loja-externa': 'nome',
    'modelo':       'nome_modelo',
    'loja':         'rotulo_display',
    'peca':         'descricao',
  };

  function debounce(fn, ms) {
    let t;
    return function(...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function buildDropdown(input) {
    const dd = document.createElement('div');
    dd.className = 'hora-autocomplete-dropdown dropdown-menu show p-0';
    dd.style.cssText =
      'position:absolute;z-index:1080;display:none;max-height:320px;'
      + 'overflow-y:auto;min-width:280px;';
    document.body.appendChild(dd);

    function position() {
      const rect = input.getBoundingClientRect();
      dd.style.top = (window.scrollY + rect.bottom + 2) + 'px';
      dd.style.left = (window.scrollX + rect.left) + 'px';
      dd.style.minWidth = rect.width + 'px';
    }

    return { dd, position };
  }

  function attach(input) {
    const tipo = input.dataset.horaAutocomplete;
    const url = ENDPOINTS[tipo];
    if (!url) {
      console.warn('hora-autocomplete: tipo desconhecido', tipo, input);
      return;
    }
    const minChars = parseInt(input.dataset.horaMinChars || '2', 10);
    const debounceMs = parseInt(input.dataset.horaDebounceMs || '200', 10);
    // FU-1 (opt-in): com data-hora-open-on-focus="1", focar/clicar o campo
    // (sem digitar) lista o top-N — envia q vazio + vazio_ok=1 ao backend.
    // Default false -> as ~20 telas existentes seguem exigindo >= minChars.
    const openOnFocus = input.dataset.horaOpenOnFocus === '1';
    const targetId = input.dataset.horaTargetId || null;
    const targetKey = input.dataset.horaTargetKey || DEFAULT_KEYS[tipo] || 'id';
    const targetEl = targetId ? document.getElementById(targetId) : null;
    // Query string extra (ex.: "sem_recebimento=1&ativo=1"). Permite que telas
    // especificas restrinjam o conjunto sem precisar de endpoint novo. Lido
    // DINAMICAMENTE no fetch (ver fetchData) — telas que mudam os filtros em
    // runtime (cascata modelo/cor -> chassi no Pedido de Venda) so atualizam o
    // dataset, sem reinicializar o autocomplete (evita dropdown duplicado).

    const { dd, position } = buildDropdown(input);

    function close() { dd.style.display = 'none'; }
    function open() { position(); dd.style.display = 'block'; }

    function render(items) {
      dd.innerHTML = '';
      if (!items || !items.length) {
        const empty = document.createElement('div');
        empty.className = 'dropdown-item-text text-muted small p-2';
        empty.textContent = 'Sem resultados';
        dd.appendChild(empty);
        open();
        return;
      }
      items.forEach(item => {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'dropdown-item small py-1 px-2';
        a.textContent = item.label || item[DEFAULT_KEYS[tipo]] || '?';
        a.addEventListener('mousedown', ev => {
          // mousedown roda antes do blur do input — assim a selecao
          // ocorre antes do dropdown sumir.
          ev.preventDefault();
          input.value = item[DEFAULT_KEYS[tipo]] || a.textContent;
          if (targetEl) {
            targetEl.value = item[targetKey] != null ? item[targetKey] : '';
            // Dispara change para forms reativos (ex.: selectStores).
            targetEl.dispatchEvent(new Event('change', { bubbles: true }));
          }
          input.dispatchEvent(new Event('change', { bubbles: true }));
          close();
        });
        dd.appendChild(a);
      });
      open();
    }

    async function fetchData(q) {
      const qNorm = q || '';
      // openOnFocus permite q VAZIO (lista top-N); 1 caractere segue cortado.
      const isEmptyTopN = openOnFocus && qNorm.length === 0;
      if (qNorm.length < minChars && !isEmptyTopN) {
        close();
        return;
      }
      try {
        let qs = `?q=${encodeURIComponent(qNorm)}`;
        // Le os filtros extra do dataset NO MOMENTO do fetch (dinamico).
        const extraParams = (input.dataset.horaExtraParams || '').replace(/^[?&]+/, '');
        if (extraParams) qs += '&' + extraParams;
        // Sinaliza ao backend que o q vazio e intencional (retorna top-N).
        if (isEmptyTopN) qs += '&vazio_ok=1';
        const resp = await fetch(`${url}${qs}`, {
          credentials: 'same-origin',
          headers: { 'Accept': 'application/json' },
        });
        if (!resp.ok) {
          close();
          return;
        }
        const data = await resp.json();
        render(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('hora-autocomplete fetch erro', err);
        close();
      }
    }

    const debounced = debounce(fetchData, debounceMs);

    // openTopN: lista top-N (q vazio) quando openOnFocus. Deduplica
    // focus+click simultaneos do 1o clique via flag in-flight (evita 2 fetches).
    let openFetchInFlight = false;
    function openTopN() {
      if (!openOnFocus || openFetchInFlight) return;
      if ((input.value || '').length >= minChars) return;
      openFetchInFlight = true;
      fetchData('').finally(() => { openFetchInFlight = false; });
    }

    input.addEventListener('input', () => debounced(input.value || ''));
    input.addEventListener('focus', () => {
      if ((input.value || '').length >= minChars) fetchData(input.value);
      else openTopN();
    });
    // Reabre a lista ao clicar com o campo ja focado (ex.: apos selecionar e
    // querer trocar) — focus nao dispara nesse caso.
    input.addEventListener('click', openTopN);
    input.addEventListener('blur', () => {
      // Pequeno delay para permitir click no dropdown.
      setTimeout(close, 150);
    });
    window.addEventListener('scroll', position, true);
    window.addEventListener('resize', position);

    // Marca como inicializado para nao reattach acidental.
    input.dataset.horaAutocompleteInited = '1';
  }

  function init(root) {
    const scope = root || document;
    scope.querySelectorAll(
      'input[data-hora-autocomplete]:not([data-hora-autocomplete-inited="1"])'
    ).forEach(attach);
  }

  // Auto-init no DOMContentLoaded e expoe init para reuso (telas que
  // geram inputs dinamicamente).
  if (document.readyState !== 'loading') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', () => init());
  }

  window.HoraAutocomplete = { init };
})();
