/* Rastreamento 360 de um chassi (tela Resumo - Motos Assai).
 *
 * Fluxo: submit do form #rastreio-chassi-form -> fetch GET rastrearUrl?chassi=
 *        -> render por secao no modal #modal-rastreio-chassi.
 *
 * Espera:
 * - window.MOTOS_ASSAI_RESUMO.rastrearUrl (ex: "/motos-assai/resumo/rastrear-chassi")
 * - Modal #modal-rastreio-chassi com tabelas #rastreio-<secao>-body e
 *   cartoes .rastreio-secao#rastreio-sec-<secao>[hidden].
 */
(function () {
  'use strict';

  var cfg = window.MOTOS_ASSAI_RESUMO || {};

  // ---- helpers -----------------------------------------------------------
  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function txt(v) {
    return (v === null || v === undefined || v === '') ? '-' : String(v);
  }
  function td(v) { return '<td>' + escapeHtml(txt(v)) + '</td>'; }
  function tdCode(v) { return '<td><code>' + escapeHtml(txt(v)) + '</code></td>'; }

  function lojaLabel(num, nome) {
    var s = txt(num);
    if (nome && nome !== '-') s += ' ' + nome;
    return s;
  }

  function valorBr(n) {
    try {
      return 'R$ ' + Number(n).toLocaleString('pt-BR', {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
      });
    } catch (e) { return 'R$ ' + n; }
  }

  // Mapa de variante de badge por status/evento (classes do design system).
  var BADGE_MAP = {
    // eventos de moto
    ESTOQUE: 'bg-info', MONTADA: 'bg-primary', PENDENTE: 'bg-warning',
    PENDENCIA_RESOLVIDA: 'bg-success', DISPONIVEL: 'bg-success',
    REVERTIDA_PARA_MONTADA: 'bg-warning', SEPARADA: 'bg-dark',
    CARREGADA: 'bg-info', FATURADA: 'bg-success', CANCELADA: 'bg-secondary',
    MOTO_FALTANDO: 'bg-danger',
    // separacao / carregamento
    EM_SEPARACAO: 'bg-info', FECHADA: 'bg-primary',
    EM_CARREGAMENTO: 'bg-info', FINALIZADO: 'bg-success', CANCELADO: 'bg-secondary',
    // match NF
    BATEU: 'bg-success', DIVERGENTE: 'bg-warning', NAO_RECONCILIADO: 'bg-secondary',
    // CCe status + tipo
    PENDENTE_CCE: 'bg-warning', APLICADA: 'bg-success', IGNORADA: 'bg-secondary',
    ERRO: 'bg-danger', CHASSI: 'bg-primary', DUPLICATAS: 'bg-info',
    ENDERECO: 'bg-info', OUTRO: 'bg-secondary',
    // recibo status
    CONCLUIDO: 'bg-success', COM_DIVERGENCIA: 'bg-warning',
    EM_CONFERENCIA: 'bg-info', RECEBIDO_AGUARDANDO_CONFERENCIA: 'bg-secondary',
    RESOLVENDO_DUPLICIDADE: 'bg-warning',
    // ficha de pendencia: categoria + origem + status
    AVARIA: 'bg-danger', FALTA_PECA: 'bg-warning', REVISAO: 'bg-info',
    VENDA: 'bg-primary', INDETERMINADA: 'bg-secondary',
    GALPAO: 'bg-primary', TRANSPORTE: 'bg-info',
    POS_VENDA_CLIENTE: 'bg-danger', POS_VENDA_LOJA: 'bg-warning',
    DEVOLUCAO: 'bg-dark', aberta: 'bg-warning', resolvida: 'bg-success',
    cancelada: 'bg-secondary',
    // movimento de peca: tipo
    ENTRADA: 'bg-success', CONSUMO: 'bg-primary', CANIBALIZACAO: 'bg-warning',
    DESCARTE: 'bg-danger', AJUSTE: 'bg-secondary',
  };

  function badge(value) {
    if (value === null || value === undefined || value === '') {
      return '<span class="text-muted">-</span>';
    }
    var cls = BADGE_MAP[value] || 'bg-secondary';
    return '<span class="badge ' + cls + '">' + escapeHtml(value) + '</span>';
  }

  // ---- renderizadores por secao -----------------------------------------
  function renderRecibos(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      var conf = it.conferido
        ? '<span class="badge bg-success">Sim</span>'
        : '<span class="badge bg-secondary">Não</span>';
      if (it.tipo_divergencia) {
        conf += ' <span class="badge bg-danger">' + escapeHtml(it.tipo_divergencia) + '</span>';
      }
      return '<tr>'
        + '<td>' + escapeHtml(txt(it.numero_recibo))
        + (it.recibo_id ? ' <span class="text-muted">#' + escapeHtml(it.recibo_id) + '</span>' : '')
        + '</td>'
        + td(it.data_recibo)
        + td(it.equipe)
        + td(it.conferente)
        + td(it.modelo_texto_recibo)
        + td(it.cor_texto)
        + '<td class="text-center">' + conf + '</td>'
        + '<td>' + badge(it.status) + '</td>'
        + '</tr>';
    }).join('');
  }

  // Montagem e Linha do tempo compartilham o mesmo layout (4 colunas).
  function renderEventosLike(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      return '<tr>'
        + td(it.ocorrido_em)
        + '<td>' + badge(it.tipo) + '</td>'
        + td(it.operador)
        + td(it.observacao)
        + '</tr>';
    }).join('');
  }

  function renderPendencias(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      return '<tr>'
        + td(it.ocorrido_em)
        + td(it.operador)
        + td(it.observacao)
        + '</tr>';
    }).join('');
  }

  function renderSeparacoes(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      return '<tr>'
        + '<td>#' + escapeHtml(txt(it.sep_id)) + '</td>'
        + '<td>' + badge(it.status) + '</td>'
        + tdCode(it.pedido_numero)
        + td(lojaLabel(it.loja_numero, it.loja_nome))
        + td(it.registrada_em)
        + td(it.operador)
        + td(it.agendamento)
        + td(it.protocolo)
        + '</tr>';
    }).join('');
  }

  function renderCarregamentos(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      return '<tr>'
        + '<td>#' + escapeHtml(txt(it.carregamento_id)) + '</td>'
        + '<td>' + badge(it.status) + '</td>'
        + tdCode(it.pedido_numero)
        + td(lojaLabel(it.loja_numero, it.loja_nome))
        + td(it.escaneado_em)
        + td(it.operador)
        + '</tr>';
    }).join('');
  }

  function renderNfs(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      var dev = it.devolvido
        ? '<span class="badge bg-danger">Devolvido</span>'
          + (it.devolvido_em ? ' <span class="small text-muted">' + escapeHtml(it.devolvido_em) + '</span>' : '')
        : '<span class="text-muted">-</span>';
      var valor = (it.valor_item !== null && it.valor_item !== undefined) ? valorBr(it.valor_item) : '-';
      return '<tr>'
        + tdCode(it.numero)
        + td(it.serie)
        + td(lojaLabel(it.loja_numero, it.loja_nome))
        + td(it.data_emissao)
        + '<td>' + badge(it.status_match) + '</td>'
        + '<td class="text-end">' + escapeHtml(valor) + '</td>'
        + '<td class="text-center">' + dev + '</td>'
        + td(it.cancelada_em)
        + '</tr>';
    }).join('');
  }

  function chassisAplicadosFmt(arr) {
    if (!arr || !arr.length) return '<span class="text-muted">-</span>';
    return arr.map(function (par) {
      if (Array.isArray(par) && par.length >= 2) {
        return '<div><code>' + escapeHtml(par[0]) + '</code> &rarr; <code>' + escapeHtml(par[1]) + '</code></div>';
      }
      return '<div><code>' + escapeHtml(String(par)) + '</code></div>';
    }).join('');
  }

  function renderCces(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      var nfref = it.nf_numero || it.numero_nf_referenciada;
      return '<tr>'
        + tdCode(it.protocolo_cce)
        + td(it.numero_cce)
        + '<td>' + badge(it.tipo_correcao) + '</td>'
        + '<td>' + badge(it.status) + '</td>'
        + td(it.sequencia_cce)
        + tdCode(nfref)
        + '<td>' + chassisAplicadosFmt(it.chassis_aplicados) + '</td>'
        + td(it.criado_em)
        + '</tr>';
    }).join('');
  }

  function renderDivergencias(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      var statusBadge = it.resolvida
        ? '<span class="badge bg-success">Resolvida</span>'
          + (it.resolvida_em ? ' <span class="small text-muted">' + escapeHtml(it.resolvida_em) + '</span>' : '')
        : '<span class="badge bg-warning">Pendente</span>';
      return '<tr>'
        + '<td>#' + escapeHtml(txt(it.div_id)) + '</td>'
        + '<td><span class="badge bg-danger">' + escapeHtml(txt(it.tipo)) + '</span></td>'
        + td(it.separacao_id ? '#' + it.separacao_id : '-')
        + td(it.carregamento_id ? '#' + it.carregamento_id : '-')
        + tdCode(it.nf_numero)
        + td(it.criada_em)
        + '<td>' + statusBadge + '</td>'
        + td(it.tipo_resolucao)
        + '</tr>';
    }).join('');
  }

  function renderFichasPendencia(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      return '<tr>'
        + '<td><a href="/motos-assai/pendencias/' + encodeURIComponent(it.pendencia_id) + '">#'
          + escapeHtml(txt(it.pendencia_id)) + '</a></td>'
        + '<td>' + badge(it.categoria) + '</td>'
        + '<td>' + badge(it.origem) + '</td>'
        + td(it.fase)
        + td(it.tratativa)
        + '<td>' + badge(it.status) + '</td>'
        + td(it.descricao)
        + td(it.aberta_em)
        + '</tr>';
    }).join('');
  }

  function renderMovimentosPeca(tbody, itens) {
    tbody.innerHTML = itens.map(function (it) {
      var custo = (it.custo_total !== null && it.custo_total !== undefined) ? valorBr(it.custo_total) : '-';
      return '<tr>'
        + '<td>' + badge(it.tipo) + '</td>'
        + td(it.peca_nome)
        + '<td class="text-end">' + escapeHtml(txt(it.quantidade)) + '</td>'
        + '<td class="text-end">' + escapeHtml(custo) + '</td>'
        + tdCode(it.chassi_origem)
        + tdCode(it.chassi_destino)
        + td(it.ocorrido_em)
        + '</tr>';
    }).join('');
  }

  // ---- cabecalho da moto + chips ----------------------------------------
  function colInfo(label, value) {
    return '<div class="col-6 col-md-3">'
      + '<div class="rastreio-label text-muted">' + escapeHtml(label) + '</div>'
      + '<div class="fw-semibold">' + escapeHtml(txt(value)) + '</div>'
      + '</div>';
  }

  function renderMoto(moto, statusEfetivo, chassi) {
    var el = document.getElementById('rastreio-moto');
    if (!moto) {
      el.innerHTML = '<div class="alert alert-info mb-0">'
        + 'Chassi <code>' + escapeHtml(chassi) + '</code> não está cadastrado em <code>assai_moto</code>, '
        + 'mas há registros relacionados abaixo.</div>';
      return;
    }
    var statusHtml = statusEfetivo ? badge(statusEfetivo) : '<span class="text-muted">sem evento</span>';
    el.innerHTML =
      '<div class="d-flex flex-wrap justify-content-between align-items-start gap-2">'
      +   '<div>'
      +     '<div class="h4 mb-1"><code>' + escapeHtml(chassi) + '</code></div>'
      +     '<div class="text-muted"><strong>' + escapeHtml(txt(moto.modelo_codigo)) + '</strong>'
      +       (moto.modelo_nome ? ' · ' + escapeHtml(moto.modelo_nome) : '') + '</div>'
      +   '</div>'
      +   '<div class="text-end"><div class="mb-1">Status atual: ' + statusHtml + '</div></div>'
      + '</div>'
      + '<div class="row g-2 mt-2 small">'
      +   colInfo('Cor', moto.cor)
      +   colInfo('Motor', moto.motor)
      +   colInfo('Ano', moto.ano)
      +   colInfo('Cadastrada em', moto.criada_em)
      + '</div>';
  }

  var CHIP_DEFS = [
    ['recibos', 'Recibo', 'fa-truck-loading'],
    ['montagem', 'Montagem', 'fa-tools'],
    ['pendencias', 'Pendência', 'fa-exclamation-triangle'],
    ['separacoes', 'Separação', 'fa-dolly'],
    ['carregamentos', 'Carregamento', 'fa-truck'],
    ['nfs', 'NFe', 'fa-file-invoice-dollar'],
    ['cces', 'CCe', 'fa-edit'],
    ['divergencias', 'Divergência', 'fa-triangle-exclamation'],
    ['fichas_pendencia', 'Ficha Pendência', 'fa-clipboard-list'],
    ['movimentos_peca', 'Movimento Peça', 'fa-right-left'],
    ['eventos', 'Eventos', 'fa-clock-rotate-left'],
  ];

  function renderChips(contadores) {
    var el = document.getElementById('rastreio-chips');
    el.innerHTML = CHIP_DEFS.map(function (d) {
      var n = (contadores && contadores[d[0]]) || 0;
      var cls = n > 0 ? 'btn-outline-primary' : 'btn-outline-secondary';
      return '<button type="button" class="btn btn-sm ' + cls + ' rastreio-chip" '
        + 'data-target="rastreio-sec-' + d[0] + '"' + (n > 0 ? '' : ' disabled') + '>'
        + '<i class="fas ' + d[2] + '"></i> ' + d[1]
        + ' <span class="badge bg-secondary">' + n + '</span></button>';
    }).join('');
  }

  // ---- orquestracao ------------------------------------------------------
  var SECTION_RENDERERS = {
    recibos: renderRecibos,
    montagem: renderEventosLike,
    pendencias: renderPendencias,
    separacoes: renderSeparacoes,
    carregamentos: renderCarregamentos,
    nfs: renderNfs,
    cces: renderCces,
    divergencias: renderDivergencias,
    fichas_pendencia: renderFichasPendencia,
    movimentos_peca: renderMovimentosPeca,
    eventos: renderEventosLike,
  };

  function setSection(key, itens) {
    var card = document.getElementById('rastreio-sec-' + key);
    var countEl = document.querySelector('[data-count-for="' + key + '"]');
    var n = itens ? itens.length : 0;
    if (countEl) countEl.textContent = n;
    if (!card) return;
    if (n > 0) {
      card.hidden = false;
      var tbody = document.getElementById('rastreio-' + key + '-body');
      var renderer = SECTION_RENDERERS[key];
      if (tbody && renderer) renderer(tbody, itens);
    } else {
      card.hidden = true;
    }
  }

  function render(data) {
    document.getElementById('rastreio-chassi-titulo').textContent = data.chassi || '';
    renderMoto(data.moto, data.status_efetivo, data.chassi);
    renderChips(data.contadores);
    setSection('recibos', data.recibos);
    setSection('montagem', data.montagem);
    setSection('pendencias', data.pendencias);
    setSection('separacoes', data.separacoes);
    setSection('carregamentos', data.carregamentos);
    setSection('nfs', data.nfs);
    setSection('cces', data.cces);
    setSection('divergencias', data.divergencias);
    setSection('fichas_pendencia', data.fichas_pendencia);
    setSection('movimentos_peca', data.movimentos_peca);
    setSection('eventos', data.eventos);
  }

  // ---- estados + modal ---------------------------------------------------
  var modalInstance = null;
  function getModal() {
    var el = document.getElementById('modal-rastreio-chassi');
    if (!el) return null;
    if (!modalInstance) modalInstance = bootstrap.Modal.getOrCreateInstance(el);
    return modalInstance;
  }

  function toggle(id, on) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle('d-none', !on);
  }

  function showState(state) {
    toggle('rastreio-loading', state === 'loading');
    toggle('rastreio-empty', state === 'empty');
    toggle('rastreio-error', state === 'error');
    toggle('rastreio-conteudo', state === 'content');
  }

  function showError(msg) {
    var el = document.getElementById('rastreio-error');
    if (el) el.textContent = msg;
    showState('error');
  }

  function rastrear(chassi) {
    var modal = getModal();
    if (modal) modal.show();
    showState('loading');

    var base = cfg.rastrearUrl || '/motos-assai/resumo/rastrear-chassi';
    var url = base + '?chassi=' + encodeURIComponent(chassi);

    fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) {
        return r.json()
          .then(function (j) { return { ok: r.ok, status: r.status, body: j }; })
          .catch(function () { return { ok: r.ok, status: r.status, body: {} }; });
      })
      .then(function (res) {
        var data = res.body || {};
        if (!res.ok || data.ok === false) {
          showError(data.erro || ('Erro ao rastrear (HTTP ' + res.status + ').'));
          return;
        }
        if (!data.encontrado) {
          var emptyEl = document.getElementById('rastreio-empty');
          if (emptyEl) emptyEl.textContent = data.mensagem || ('Nenhum registro para o chassi ' + chassi + '.');
          showState('empty');
          return;
        }
        render(data);
        showState('content');
      })
      .catch(function (err) {
        showError('Erro de rede: ' + err.message);
      });
  }

  // ---- listeners (script defer => DOM ja parseado) -----------------------
  var form = document.getElementById('rastreio-chassi-form');
  if (form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var input = document.getElementById('rastreio-chassi-input');
      var chassi = (input && input.value || '').trim();
      if (!chassi) { if (input) input.focus(); return; }
      rastrear(chassi);
    });
  }

  // Chips: rola ate a secao correspondente dentro do modal.
  document.addEventListener('click', function (ev) {
    var chip = ev.target.closest('.rastreio-chip');
    if (!chip || chip.disabled) return;
    var target = document.getElementById(chip.getAttribute('data-target'));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
})();
