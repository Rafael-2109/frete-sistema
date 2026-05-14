/* eslint-disable no-console */
/**
 * Aba "Historico" da tela rica /cmdk/pedido/<num_pedido>.
 *
 * - Carrega dados via GET /api/cmdk/pedido/<num>/historico (lazy, 1x por sessao)
 * - Renderiza sumario + timeline cronologica de momentos agregados
 * - Expansao por linha mostra diff antes/depois dos campos relevantes
 *
 * Backend: app/cmdk/services/historico_pedido.py (le evento_supply_chain).
 */
(function () {
  'use strict';

  const TAB_BTN_ID = 'raio-x-tab-historico-btn';
  const ROOT_SELECTOR = '.raio-x-historico';

  // Estado da aba (dados carregados + filtros aplicados)
  const state = {
    numPedido: null,
    momentos: [],        // lista original (imutavel apos load)
    filtrados: [],       // resultado dos filtros
    filtros: criarFiltrosVazios(),
  };

  function criarFiltrosVazios() {
    return { entidade: '', tipo: '', origem: '', usuario: '', dataDe: '', dataAte: '' };
  }

  document.addEventListener('DOMContentLoaded', function () {
    const tabBtn = document.getElementById(TAB_BTN_ID);
    if (!tabBtn) return;

    const root = document.querySelector(ROOT_SELECTOR);
    if (!root) return;

    let loadState = 'idle'; // idle | loading | loaded | error

    tabBtn.addEventListener('shown.bs.tab', function () {
      if (loadState === 'loading' || loadState === 'loaded') return;
      loadState = 'loading';
      carregar(root, function (sucesso) {
        loadState = sucesso ? 'loaded' : 'error';
      });
    });

    // Retry: clicar no estado de erro tenta de novo
    const errEl = document.getElementById('raio-x-historico-error');
    if (errEl) {
      errEl.style.cursor = 'pointer';
      errEl.title = 'Clique para tentar novamente';
      errEl.addEventListener('click', function () {
        if (loadState !== 'error') return;
        errEl.hidden = true;
        const loadEl = document.getElementById('raio-x-historico-loading');
        if (loadEl) loadEl.hidden = false;
        loadState = 'loading';
        carregar(root, function (sucesso) {
          loadState = sucesso ? 'loaded' : 'error';
        });
      });
    }

    bindFiltros();
  });

  function bindFiltros() {
    const ids = [
      'raio-x-hist-f-entidade', 'raio-x-hist-f-tipo', 'raio-x-hist-f-origem',
      'raio-x-hist-f-usuario', 'raio-x-hist-f-data-de', 'raio-x-hist-f-data-ate'
    ];
    ids.forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', onFiltroChange);
    });

    const btnLimpar = document.getElementById('raio-x-hist-btn-limpar');
    if (btnLimpar) btnLimpar.addEventListener('click', limparFiltros);

    const btnExport = document.getElementById('raio-x-hist-btn-export');
    if (btnExport) btnExport.addEventListener('click', exportarCSV);
  }

  function onFiltroChange() {
    state.filtros = lerFiltrosDaUI();
    aplicarFiltros();
  }

  function lerFiltrosDaUI() {
    return {
      entidade: valOf('raio-x-hist-f-entidade'),
      tipo:     valOf('raio-x-hist-f-tipo'),
      origem:   valOf('raio-x-hist-f-origem'),
      usuario:  valOf('raio-x-hist-f-usuario'),
      dataDe:   valOf('raio-x-hist-f-data-de'),
      dataAte:  valOf('raio-x-hist-f-data-ate'),
    };
  }

  function valOf(id) {
    const el = document.getElementById(id);
    return el ? (el.value || '').trim() : '';
  }

  function limparFiltros() {
    ['raio-x-hist-f-entidade', 'raio-x-hist-f-tipo', 'raio-x-hist-f-origem',
     'raio-x-hist-f-usuario', 'raio-x-hist-f-data-de', 'raio-x-hist-f-data-ate']
      .forEach(function (id) {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
    state.filtros = criarFiltrosVazios();
    aplicarFiltros();
  }

  function carregar(root, onComplete) {
    const cb = typeof onComplete === 'function' ? onComplete : function () {};

    const numPedido = root.getAttribute('data-num-pedido');
    if (!numPedido) {
      mostrarErro(root, 'Pedido sem identificacao.');
      cb(false);
      return;
    }

    const url = '/api/cmdk/pedido/' + encodeURIComponent(numPedido) + '/historico';

    fetch(url, {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    })
      .then(function (resp) {
        if (!resp.ok) {
          throw new Error('HTTP ' + resp.status);
        }
        return resp.json();
      })
      .then(function (data) {
        if (!data || data.success === false) {
          throw new Error(data && data.error ? data.error : 'Resposta invalida');
        }
        renderizar(root, data);
        cb(true);
      })
      .catch(function (err) {
        console.error('[historico-pedido] erro', err);
        mostrarErro(root, err.message || 'Erro ao carregar historico.');
        cb(false);
      });
  }

  function renderizar(root, data) {
    setHidden('raio-x-historico-loading', true);
    setHidden('raio-x-historico-error', true);

    const vazioEl = document.getElementById('raio-x-historico-vazio');
    const contentEl = document.getElementById('raio-x-historico-content');

    if (data.vazio || !data.momentos || data.momentos.length === 0) {
      if (vazioEl) vazioEl.hidden = false;
      if (contentEl) contentEl.hidden = true;
      return;
    }

    if (vazioEl) vazioEl.hidden = true;
    if (contentEl) contentEl.hidden = false;

    // Persiste dados originais no estado
    state.numPedido = data.num_pedido || null;
    state.momentos = data.momentos.slice(); // copia defensiva
    state.filtros = criarFiltrosVazios();

    // Sumario
    const s = data.sumario || {};
    setText('raio-x-hist-total', formatNumero(s.total_eventos));
    setText('raio-x-hist-periodo', formatPeriodo(s.primeiro_evento, s.ultimo_evento));
    setText('raio-x-hist-produtos', listaCount(s.produtos));
    setText('raio-x-hist-nfs', listaCount(s.notas_fiscais));
    setText('raio-x-hist-lotes', listaCount(s.lotes_separacao));
    setText('raio-x-hist-usuarios', formatNumero(s.usuarios_distintos));

    // Badge no botao da aba
    const badge = document.getElementById('raio-x-historico-badge');
    if (badge) {
      badge.textContent = formatNumero(s.total_eventos);
      badge.hidden = false;
    }

    popularDropdowns(state.momentos);
    aplicarFiltros();
  }

  /**
   * Popula <select> de filtros com valores unicos da lista de momentos.
   * Cada select preserva sua opcao "Todos/Todas" (primeira <option>).
   */
  function popularDropdowns(momentos) {
    popularSelect('raio-x-hist-f-entidade', valoresUnicos(momentos, 'entidade'));
    popularSelect('raio-x-hist-f-tipo',     valoresUnicos(momentos, 'tipo_evento'));
    popularSelect('raio-x-hist-f-origem',   valoresUnicos(momentos, 'origem'));
    popularSelect('raio-x-hist-f-usuario',  valoresUnicos(momentos, 'registrado_por'));
  }

  function valoresUnicos(arr, campo) {
    const set = new Set();
    arr.forEach(function (m) {
      const v = m[campo];
      if (v !== null && v !== undefined && v !== '') set.add(v);
    });
    return Array.from(set).sort(function (a, b) {
      return String(a).localeCompare(String(b), 'pt-BR');
    });
  }

  function popularSelect(id, valores) {
    const sel = document.getElementById(id);
    if (!sel) return;
    // Remove opcoes anteriores exceto a primeira (placeholder "Todos")
    while (sel.options.length > 1) sel.remove(1);
    valores.forEach(function (v) {
      const opt = document.createElement('option');
      opt.value = String(v);
      opt.textContent = String(v);
      sel.appendChild(opt);
    });
  }

  /**
   * Aplica filtros combinados (AND) sobre state.momentos -> state.filtrados.
   * Re-renderiza timeline e contador.
   */
  function aplicarFiltros() {
    const f = state.filtros;
    state.filtrados = state.momentos.filter(function (m) {
      if (f.entidade && m.entidade !== f.entidade) return false;
      if (f.tipo     && m.tipo_evento !== f.tipo) return false;
      if (f.origem   && m.origem !== f.origem) return false;
      if (f.usuario  && m.registrado_por !== f.usuario) return false;
      if (f.dataDe || f.dataAte) {
        const dataMomento = extrairDataISO(m.quando_iso); // 'YYYY-MM-DD'
        if (!dataMomento) return false;
        if (f.dataDe && dataMomento < f.dataDe) return false;
        if (f.dataAte && dataMomento > f.dataAte) return false;
      }
      return true;
    });

    renderTimeline(state.filtrados);
    atualizarContador(state.filtrados.length, state.momentos.length);
  }

  function extrairDataISO(iso) {
    if (!iso) return null;
    // 'YYYY-MM-DDTHH:MM:SS' -> 'YYYY-MM-DD'
    const m = String(iso).match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : null;
  }

  function renderTimeline(momentos) {
    const tl = document.getElementById('raio-x-hist-timeline');
    const semResultado = document.getElementById('raio-x-hist-sem-resultado');
    if (!tl) return;

    tl.innerHTML = '';

    if (!momentos.length) {
      tl.hidden = true;
      if (semResultado) semResultado.hidden = false;
      return;
    }

    tl.hidden = false;
    if (semResultado) semResultado.hidden = true;
    momentos.forEach(function (m, idx) {
      tl.appendChild(criarLinhaTimeline(m, idx));
    });
  }

  function atualizarContador(visiveis, total) {
    const el = document.getElementById('raio-x-hist-contador');
    if (!el) return;
    if (visiveis === total) {
      el.textContent = total + (total === 1 ? ' momento' : ' momentos');
    } else {
      el.textContent = visiveis + ' de ' + total + ' momentos';
    }
  }

  /**
   * Exporta os momentos atualmente visiveis (state.filtrados) em CSV.
   * Inclui: quando, entidade, tipo, origem, usuario, qtd_produtos,
   * campos_alterados, e cada par campo:de->para de mudancas.
   */
  function exportarCSV() {
    const lista = state.filtrados.length ? state.filtrados : state.momentos;
    if (!lista.length) {
      alert('Nenhum momento para exportar.');
      return;
    }

    const headers = [
      'quando', 'entidade', 'tipo_evento', 'origem', 'registrado_por',
      'qtd_produtos', 'campos_alterados', 'mudancas'
    ];
    const linhas = [headers.map(csvEscape).join(',')];

    lista.forEach(function (m) {
      const mudStr = m.mudancas
        ? Object.keys(m.mudancas).map(function (k) {
            const mu = m.mudancas[k];
            return k + ': ' + valorPlano(mu.de) + ' -> ' + valorPlano(mu.para);
          }).join(' | ')
        : '';
      const camposStr = (m.campos_alterados || []).join(', ');
      // Usa quando_iso para ter ano + segundos (ordenavel em Excel),
      // com fallback para quando_label se ISO ausente.
      const quandoCSV = formatQuandoCSV(m.quando_iso) || m.quando_label || '';
      linhas.push([
        quandoCSV,
        m.entidade || '',
        m.tipo_evento || '',
        m.origem || '',
        m.registrado_por || '',
        m.qtd_produtos || 0,
        camposStr,
        mudStr
      ].map(csvEscape).join(','));
    });

    const conteudo = '﻿' + linhas.join('\r\n'); // BOM UTF-8 para Excel
    const blob = new Blob([conteudo], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'historico_' + (state.numPedido || 'pedido') + '.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function csvEscape(v) {
    if (v === null || v === undefined) return '';
    let s = String(v);
    // Defesa contra formula injection no Excel/LibreOffice: valores que comecam
    // com =, +, -, @, TAB ou CR sao avaliados como formula. Prefixa com aspa simples.
    if (/^[=+\-@\t\r]/.test(s)) {
      s = "'" + s;
    }
    if (s.indexOf(',') !== -1 || s.indexOf('"') !== -1 || s.indexOf('\n') !== -1) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  function valorPlano(v) {
    if (v === null || v === undefined) return '∅';
    return String(v);
  }

  /**
   * Formata 'YYYY-MM-DDTHH:MM:SS.fff' (Brasilia naive) -> 'YYYY-MM-DD HH:MM:SS'
   * para o CSV (ordenavel em Excel, com ano e segundos).
   */
  function formatQuandoCSV(iso) {
    if (!iso) return '';
    const limpo = String(iso).replace(/Z$/, '').replace(/[+-]\d{2}:?\d{2}$/, '');
    const m = limpo.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/);
    return m ? (m[1] + ' ' + m[2]) : limpo;
  }

  function criarLinhaTimeline(momento, idx) {
    const item = document.createElement('div');
    item.className = 'raio-x-hist-item'
      + ' raio-x-hist-item--' + slug(momento.entidade)
      + ' raio-x-hist-item--' + slug(momento.tipo_evento);
    item.setAttribute('role', 'listitem');

    const temMudancas = momento.mudancas && Object.keys(momento.mudancas).length > 0;
    const expansivel = temMudancas;
    if (expansivel) {
      item.classList.add('raio-x-hist-item--expansivel');
      item.tabIndex = 0;
    }

    // Cabecalho (linha clicavel)
    const header = document.createElement('div');
    header.className = 'raio-x-hist-item__header';

    // Coluna 1: timestamp + icone origem
    const colQuando = document.createElement('div');
    colQuando.className = 'raio-x-hist-item__quando';
    colQuando.innerHTML = '<i class="' + iconeOrigem(momento.origem) + '"></i> '
      + '<span class="raio-x-hist-item__data">' + escapeHtml(momento.quando_label) + '</span>';
    if (momento.quando_iso) {
      colQuando.title = momento.quando_iso;
    }
    header.appendChild(colQuando);

    // Coluna 2: badges entidade + tipo
    const colBadges = document.createElement('div');
    colBadges.className = 'raio-x-hist-item__badges';
    colBadges.innerHTML =
      '<span class="raio-x-hist-badge raio-x-hist-badge--ent-' + slug(momento.entidade) + '">'
        + escapeHtml(momento.entidade) + '</span>'
      + '<span class="raio-x-hist-badge raio-x-hist-badge--tipo-' + slug(momento.tipo_evento) + '">'
        + escapeHtml(momento.tipo_evento) + '</span>';
    header.appendChild(colBadges);

    // Coluna 3: usuario + qtd produtos + campos resumo
    const colInfo = document.createElement('div');
    colInfo.className = 'raio-x-hist-item__info';

    const userLine = document.createElement('div');
    userLine.className = 'raio-x-hist-item__user';
    userLine.textContent = momento.registrado_por || '—';
    colInfo.appendChild(userLine);

    const meta = document.createElement('div');
    meta.className = 'raio-x-hist-item__meta';
    const partes = [];
    if (momento.qtd_produtos > 1) {
      partes.push(momento.qtd_produtos + ' produtos');
    } else if (momento.qtd_produtos === 1) {
      partes.push('1 produto');
    }
    if (momento.origem) {
      partes.push(momento.origem);
    }
    if (momento.campos_alterados && momento.campos_alterados.length) {
      partes.push('campos: ' + momento.campos_alterados.join(', '));
    }
    meta.textContent = partes.join(' · ');
    colInfo.appendChild(meta);

    header.appendChild(colInfo);

    // Coluna 4: chevron
    if (expansivel) {
      const colChevron = document.createElement('div');
      colChevron.className = 'raio-x-hist-item__chevron';
      colChevron.innerHTML = '<i class="fas fa-chevron-down"></i>';
      header.appendChild(colChevron);
    }

    item.appendChild(header);

    // Detalhe (mudancas)
    if (temMudancas) {
      const detalhe = document.createElement('div');
      detalhe.className = 'raio-x-hist-item__detalhe';
      detalhe.hidden = true;

      const tabela = document.createElement('table');
      tabela.className = 'raio-x-hist-diff';
      tabela.innerHTML = '<thead><tr>'
        + '<th>Campo</th><th>De</th><th>Para</th>'
        + '</tr></thead>';
      const tbody = document.createElement('tbody');

      Object.keys(momento.mudancas).forEach(function (campo) {
        const m = momento.mudancas[campo];
        const tr = document.createElement('tr');
        tr.innerHTML =
          '<td class="raio-x-hist-diff__campo">' + escapeHtml(campo) + '</td>'
          + '<td class="raio-x-hist-diff__de">' + formatValor(m.de) + '</td>'
          + '<td class="raio-x-hist-diff__para">' + formatValor(m.para) + '</td>';
        tbody.appendChild(tr);
      });

      tabela.appendChild(tbody);
      detalhe.appendChild(tabela);

      if (momento.cod_produto_amostra && momento.qtd_produtos > 1) {
        const nota = document.createElement('div');
        nota.className = 'raio-x-hist-item__detalhe-nota';
        nota.textContent = 'Diff mostrado para ' + momento.cod_produto_amostra
          + ' (amostra dos ' + momento.qtd_produtos + ' produtos do momento).';
        detalhe.appendChild(nota);
      }

      item.appendChild(detalhe);

      // Toggle
      const toggle = function () {
        const open = item.classList.toggle('raio-x-hist-item--open');
        detalhe.hidden = !open;
      };
      header.addEventListener('click', toggle);
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggle();
        }
      });
    }

    return item;
  }

  // ───────────────────────────── helpers

  function mostrarErro(root, msg) {
    setHidden('raio-x-historico-loading', true);
    setHidden('raio-x-historico-content', true);
    const errEl = document.getElementById('raio-x-historico-error');
    if (!errEl) return;
    errEl.hidden = false;
    const msgEl = errEl.querySelector('[data-msg]');
    if (msgEl) msgEl.textContent = msg;
  }

  function setHidden(id, hidden) {
    const el = document.getElementById(id);
    if (el) el.hidden = !!hidden;
  }

  function setText(id, txt) {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  }

  function iconeOrigem(origem) {
    switch ((origem || '').toUpperCase()) {
      case 'SYNC_ODOO':    return 'fas fa-sync-alt';
      case 'USUARIO':      return 'fas fa-user';
      case 'UPLOAD_EXCEL': return 'fas fa-file-excel';
      case 'SISTEMA':      return 'fas fa-cog';
      default:             return 'fas fa-circle';
    }
  }

  function slug(s) {
    return (s || 'na').toString().toLowerCase().replace(/[^a-z0-9]+/g, '-');
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatValor(v) {
    if (v === null || v === undefined) {
      return '<span class="raio-x-hist-diff__null">∅</span>';
    }
    if (v === true)  return '<span class="raio-x-hist-diff__bool">true</span>';
    if (v === false) return '<span class="raio-x-hist-diff__bool">false</span>';
    return '<span class="raio-x-hist-diff__val">' + escapeHtml(String(v)) + '</span>';
  }

  function formatNumero(n) {
    if (n === null || n === undefined) return '—';
    try {
      return Number(n).toLocaleString('pt-BR');
    } catch (e) {
      return String(n);
    }
  }

  function listaCount(arr) {
    if (!arr || !arr.length) return '0';
    if (arr.length <= 3) {
      return arr.length + ' (' + arr.join(', ') + ')';
    }
    return arr.length + ' (' + arr.slice(0, 3).join(', ') + ', …)';
  }

  function formatPeriodo(ini, fim) {
    if (!ini && !fim) return '—';
    const a = formatDataISO(ini);
    const b = formatDataISO(fim);
    if (a && b && a === b) return a;
    return (a || '—') + ' → ' + (b || '—');
  }

  function formatDataISO(iso) {
    if (!iso) return '';
    try {
      // evento_supply_chain.registrado_em vem em Brasilia naive
      // (gravado pelo trigger PG no mesmo instante que Python agora_utc_naive()
      // grava criado_em). Trata como local time, sem conversao.
      const limpo = iso.replace(/Z$/, '').replace(/[+-]\d{2}:?\d{2}$/, '');
      const partes = limpo.split('T');
      if (partes.length < 2) return iso;
      const [data, hora] = partes;
      const [yyyy, mm, dd] = data.split('-');
      const [hh, mi] = hora.split(':');
      return dd + '/' + mm + '/' + yyyy + ' ' + hh + ':' + mi;
    } catch (e) {
      return iso || '';
    }
  }
})();
