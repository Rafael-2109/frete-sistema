/* Resumo Motos Assai - modais lazy-load por (modelo, status).
 *
 * Espera:
 * - window.MOTOS_ASSAI_RESUMO.detalheUrlBase ex: "/motos-assai/resumo/"
 * - Botoes com data-modelo-id, data-modelo-codigo, data-status, data-status-label
 * - Modal #modal-resumo-detalhe + tabelas #resumo-modal-table-<status>
 */
(function () {
  'use strict';

  var cfg = window.MOTOS_ASSAI_RESUMO || {};

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function buildUrl(modeloId, status) {
    var base = (cfg.detalheUrlBase || '/motos-assai/resumo/').replace(/\/+$/, '/');
    return base + modeloId + '/' + status;
  }

  function showOnly(status) {
    var allTables = document.querySelectorAll('[id^="resumo-modal-table-"]');
    allTables.forEach(function (el) { el.classList.add('d-none'); });
    var target = document.getElementById('resumo-modal-table-' + status);
    if (target) target.classList.remove('d-none');
    return target;
  }

  function renderEstoque(tbody, itens) {
    var html = '';
    itens.forEach(function (it, idx) {
      html += '<tr>'
        + '<td>' + (idx + 1) + '</td>'
        + '<td><code>' + escapeHtml(it.chassi) + '</code></td>'
        + '<td>' + escapeHtml(it.cor) + '</td>'
        + '<td>' + escapeHtml(it.data_recebimento) + '</td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  function renderPendente(tbody, itens) {
    var html = '';
    itens.forEach(function (it, idx) {
      html += '<tr>'
        + '<td>' + (idx + 1) + '</td>'
        + '<td><code>' + escapeHtml(it.chassi) + '</code></td>'
        + '<td>' + escapeHtml(it.cor) + '</td>'
        + '<td>' + escapeHtml(it.data_pendencia) + '</td>'
        + '<td>' + escapeHtml(it.operador) + '</td>'
        + '<td>' + escapeHtml(it.observacao) + '</td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  function renderMontada(tbody, itens) {
    var html = '';
    itens.forEach(function (it, idx) {
      var tipoBadge = it.tipo === 'REVERTIDA_PARA_MONTADA'
        ? '<span class="badge bg-warning text-dark">' + escapeHtml(it.tipo) + '</span>'
        : '<span class="badge bg-primary">' + escapeHtml(it.tipo || 'MONTADA') + '</span>';
      html += '<tr>'
        + '<td>' + (idx + 1) + '</td>'
        + '<td><code>' + escapeHtml(it.chassi) + '</code></td>'
        + '<td>' + escapeHtml(it.cor) + '</td>'
        + '<td>' + tipoBadge + '</td>'
        + '<td>' + escapeHtml(it.operador) + '</td>'
        + '<td>' + escapeHtml(it.data_hora) + '</td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  function renderDisponivel(tbody, itens) {
    var html = '';
    itens.forEach(function (it, idx) {
      html += '<tr>'
        + '<td>' + (idx + 1) + '</td>'
        + '<td><code>' + escapeHtml(it.chassi) + '</code></td>'
        + '<td>' + escapeHtml(it.cor) + '</td>'
        + '<td>' + escapeHtml(it.montagem_operador) + '</td>'
        + '<td>' + escapeHtml(it.montagem_data) + '</td>'
        + '<td>' + escapeHtml(it.disp_operador) + '</td>'
        + '<td>' + escapeHtml(it.disp_data) + '</td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  function renderEmPedido(tbody, itens) {
    var html = '';
    itens.forEach(function (it) {
      html += '<tr>'
        + '<td><strong>' + escapeHtml(it.loja_numero) + '</strong> ' + escapeHtml(it.loja_nome) + '</td>'
        + '<td>' + escapeHtml(it.loja_cidade) + '/' + escapeHtml(it.loja_uf) + '</td>'
        + '<td><code>' + escapeHtml(it.pedido_numero) + '</code></td>'
        + '<td><span class="badge bg-secondary">' + escapeHtml(it.pedido_status) + '</span></td>'
        + '<td class="text-end">' + it.qtd_pedida + '</td>'
        + '<td class="text-end">' + it.qtd_faturada + '</td>'
        + '<td class="text-end"><strong>' + it.qtd_pendente + '</strong></td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  var RENDERERS = {
    estoque: renderEstoque,
    pendente: renderPendente,
    montada: renderMontada,
    disponivel: renderDisponivel,
    em_pedido: renderEmPedido,
  };

  function openModal(modeloId, modeloCodigo, status, statusLabel) {
    var modalEl = document.getElementById('modal-resumo-detalhe');
    if (!modalEl) return;

    document.getElementById('resumo-modal-titulo').textContent =
      modeloCodigo + ' - ' + statusLabel;

    var loadingEl = document.getElementById('resumo-modal-loading');
    var emptyEl = document.getElementById('resumo-modal-empty');
    loadingEl.classList.remove('d-none');
    emptyEl.classList.add('d-none');
    showOnly(null); // esconde todas as tabelas

    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    fetch(buildUrl(modeloId, status), {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        loadingEl.classList.add('d-none');
        var itens = (data && data.itens) || [];
        if (itens.length === 0) {
          emptyEl.classList.remove('d-none');
          return;
        }
        var table = showOnly(status);
        if (table) {
          var tbody = table.querySelector('tbody');
          var renderer = RENDERERS[status];
          if (renderer && tbody) renderer(tbody, itens);
        }
      })
      .catch(function (err) {
        loadingEl.classList.add('d-none');
        emptyEl.classList.remove('d-none');
        emptyEl.textContent = 'Erro ao carregar: ' + err.message;
      });
  }

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.resumo-btn');
    if (!btn || btn.disabled) return;
    var modeloId = btn.getAttribute('data-modelo-id');
    var modeloCodigo = btn.getAttribute('data-modelo-codigo');
    var status = btn.getAttribute('data-status');
    var statusLabel = btn.getAttribute('data-status-label');
    if (!modeloId || !status) return;
    openModal(modeloId, modeloCodigo, status, statusLabel);
  });
})();
