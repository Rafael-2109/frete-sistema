/**
 * pallet-unified.js — Logica Frontend da Tela Unificada de Pallets V3
 *
 * 6 Modulos:
 * - PalletKPIs: Carrega e atualiza KPIs + alertas
 * - PalletTable: Renderiza tabela + paginacao + ordenacao
 * - PalletFilters: Gerencia filtros + debounce + URL sync
 * - PalletDetail: Offcanvas com carregamento AJAX
 * - PalletModals: 10 modais com validacao e submit
 * - PalletSync: Botoes sync Odoo + processar DFe
 */

(function () {
  'use strict';

  const API_BASE = '/pallet/v3';
  const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 min

  // ========================================================================
  // HELPERS
  // ========================================================================

  async function apiFetch(url, options = {}) {
    const defaults = {
      headers: { 'Content-Type': 'application/json' },
    };
    const config = { ...defaults, ...options };
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
      config.body = JSON.stringify(config.body);
    }

    try {
      const res = await fetch(url, config);
      const data = await res.json();
      if (!res.ok || !data.sucesso) {
        throw new Error(data.mensagem || `Erro HTTP ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error(`[PalletV3] Erro em ${url}:`, err);
      throw err;
    }
  }

  function showToast(msg, type = 'success') {
    if (window.toastr) {
      toastr[type](msg, '', { timeOut: 3000, positionClass: 'toast-top-right' });
    } else {
      console.log(`[${type}] ${msg}`);
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function formatCnpj(v) {
    if (!v) return '-';
    const d = String(v).replace(/\D/g, '');
    if (d.length === 14) return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    if (d.length === 11) return d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
    return v;
  }

  function formatDateBr(v) {
    if (!v) return '-';
    const d = new Date(v);
    if (isNaN(d)) return v;
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  // ========================================================================
  // MODULE: PalletKPIs
  // ========================================================================

  const PalletKPIs = {
    async load() {
      try {
        const { dados } = await apiFetch(`${API_BASE}/api/kpis`);
        document.getElementById('kpiEmTerceiros').textContent = dados.em_terceiros.toLocaleString('pt-BR');
        document.getElementById('kpiSaldoPendente').textContent = dados.saldo_pendente.toLocaleString('pt-BR');
        document.getElementById('kpiCreditosAbertos').textContent = dados.creditos_abertos.toLocaleString('pt-BR');
        document.getElementById('kpiVencendo7d').textContent = dados.vencendo_7d.toLocaleString('pt-BR');
        document.getElementById('kpiSugestoes').textContent = dados.sugestoes_pendentes.toLocaleString('pt-BR');
        document.getElementById('kpiDocsPendentes').textContent = dados.docs_nao_recebidos.toLocaleString('pt-BR');

        // Alertas
        this.renderAlertas(dados.alertas || []);
      } catch (err) {
        console.error('[KPIs] Falha ao carregar:', err);
      }
    },

    renderAlertas(alertas) {
      const container = document.getElementById('alertasContainer');
      if (!alertas.length) {
        container.style.display = 'none';
        return;
      }
      container.style.display = 'flex';
      container.innerHTML = alertas.map(a => `
        <div class="pu-alerta pu-alerta--${a.tipo}" data-filtro='${JSON.stringify(a.filtro)}'>
          <i class="${a.icone}"></i> ${escapeHtml(a.texto)}
        </div>
      `).join('');

      // Click handler para alertas
      container.querySelectorAll('.pu-alerta').forEach(el => {
        el.addEventListener('click', () => {
          const filtro = JSON.parse(el.dataset.filtro);
          PalletFilters.applyFromAlert(filtro);
        });
      });
    }
  };

  // ========================================================================
  // MODULE: PalletFilters
  // ========================================================================

  const PalletFilters = {
    _debounceTimer: null,
    _currentAba: 'visao_geral',

    init() {
      // Inputs de texto com debounce
      ['filtroBusca', 'filtroCnpj'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', () => this._debounced());
      });

      // Selects com change imediato
      ['filtroStatusNf', 'filtroStatusCredito', 'filtroEmpresa', 'filtroTipo',
       'filtroUf', 'filtroCidade'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => this._refresh());
      });

      // Datas
      ['filtroDataDe', 'filtroDataAte'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => this._refresh());
      });

      // UF -> Cidade dependente
      const ufSelect = document.getElementById('filtroUf');
      if (ufSelect) {
        ufSelect.addEventListener('change', async () => {
          const cidadeSelect = document.getElementById('filtroCidade');
          const uf = ufSelect.value;
          cidadeSelect.innerHTML = '<option value="">Cidade</option>';
          if (uf) {
            try {
              const { dados } = await apiFetch(`${API_BASE}/api/filtros/cidades?uf=${uf}`);
              dados.forEach(c => {
                cidadeSelect.innerHTML += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
              });
              cidadeSelect.disabled = false;
            } catch (e) { /* ignore */ }
          } else {
            cidadeSelect.disabled = true;
          }
        });
      }

      // Abas
      document.querySelectorAll('#tabsContainer .nav-link').forEach(tab => {
        tab.addEventListener('click', (e) => {
          e.preventDefault();
          document.querySelectorAll('#tabsContainer .nav-link').forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          this._currentAba = tab.dataset.aba;
          this._refresh();
        });
      });

      // Limpar filtros
      const btnLimpar = document.getElementById('btnLimparFiltros');
      if (btnLimpar) btnLimpar.addEventListener('click', () => this.clear());
    },

    getAll() {
      return {
        busca: (document.getElementById('filtroBusca') || {}).value || '',
        status_nf: (document.getElementById('filtroStatusNf') || {}).value || '',
        status_credito: (document.getElementById('filtroStatusCredito') || {}).value || '',
        empresa: (document.getElementById('filtroEmpresa') || {}).value || '',
        tipo_destinatario: (document.getElementById('filtroTipo') || {}).value || '',
        cnpj: (document.getElementById('filtroCnpj') || {}).value || '',
        data_de: (document.getElementById('filtroDataDe') || {}).value || '',
        data_ate: (document.getElementById('filtroDataAte') || {}).value || '',
        uf: (document.getElementById('filtroUf') || {}).value || '',
        cidade: (document.getElementById('filtroCidade') || {}).value || '',
        aba: this._currentAba,
      };
    },

    clear() {
      ['filtroBusca', 'filtroStatusNf', 'filtroStatusCredito', 'filtroEmpresa',
       'filtroTipo', 'filtroCnpj', 'filtroDataDe', 'filtroDataAte',
       'filtroUf', 'filtroCidade'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      document.getElementById('filtroCidade').disabled = true;
      this._refresh();
    },

    applyFromAlert(filtro) {
      if (filtro.aba) {
        document.querySelectorAll('#tabsContainer .nav-link').forEach(t => {
          t.classList.toggle('active', t.dataset.aba === filtro.aba);
        });
        this._currentAba = filtro.aba;
      }
      if (filtro.vencido) {
        // Vencidos: ir para aba vencendo
        document.querySelectorAll('#tabsContainer .nav-link').forEach(t => {
          t.classList.toggle('active', t.dataset.aba === 'vencendo');
        });
        this._currentAba = 'vencendo';
      }
      this._refresh();
    },

    _debounced() {
      clearTimeout(this._debounceTimer);
      this._debounceTimer = setTimeout(() => this._refresh(), 350);
    },

    _refresh() {
      PalletTable.load(1);
    }
  };

  // ========================================================================
  // MODULE: PalletTable
  // ========================================================================

  const PalletTable = {
    _currentPage: 1,
    _sortBy: 'data_emissao',
    _sortOrder: 'desc',
    _selectedIds: new Set(),

    init() {
      // Ordenacao
      document.querySelectorAll('.pu-table__th--sortable').forEach(th => {
        th.addEventListener('click', () => {
          const col = th.dataset.sort;
          if (this._sortBy === col) {
            this._sortOrder = this._sortOrder === 'asc' ? 'desc' : 'asc';
          } else {
            this._sortBy = col;
            this._sortOrder = 'desc';
          }
          // Atualizar indicadores
          document.querySelectorAll('.pu-table__th--sortable').forEach(t => {
            t.classList.remove('sorted-asc', 'sorted-desc');
          });
          th.classList.add(this._sortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');
          this.load(1);
        });
      });

      // Check all
      const checkAll = document.getElementById('checkAll');
      if (checkAll) {
        checkAll.addEventListener('change', () => {
          document.querySelectorAll('.pu-row-check').forEach(cb => {
            cb.checked = checkAll.checked;
            const id = parseInt(cb.dataset.creditoId);
            if (checkAll.checked) this._selectedIds.add(id);
            else this._selectedIds.delete(id);
          });
        });
      }
    },

    async load(page = 1) {
      this._currentPage = page;
      const body = document.getElementById('tabelaBody');
      body.innerHTML = `<tr><td colspan="13" class="text-center py-4">
        <div class="spinner-border spinner-border-sm text-primary"></div>
        <span class="ms-2 text-muted">Carregando...</span>
      </td></tr>`;

      try {
        const filtros = PalletFilters.getAll();
        const params = new URLSearchParams({
          ...filtros,
          page: page,
          per_page: 50,
          ordenar_por: this._sortBy,
          ordem: this._sortOrder
        });

        const { dados } = await apiFetch(`${API_BASE}/api/tabela?${params}`);
        this._render(dados);
        this._renderPagination(dados);
        this._loadContadores();
      } catch (err) {
        body.innerHTML = `<tr><td colspan="13" class="pu-empty">
          <i class="fas fa-exclamation-circle"></i>
          <div class="pu-empty__text">Erro ao carregar dados</div>
        </td></tr>`;
      }
    },

    _render(dados) {
      const body = document.getElementById('tabelaBody');

      if (!dados.itens || !dados.itens.length) {
        body.innerHTML = `<tr><td colspan="13" class="pu-empty">
          <i class="fas fa-inbox"></i>
          <div class="pu-empty__text">Nenhuma NF encontrada com estes filtros</div>
        </td></tr>`;
        return;
      }

      body.innerHTML = dados.itens.map(item => this._renderRow(item)).join('');

      // Event listeners para linhas
      body.querySelectorAll('tr[data-nf-id]').forEach(tr => {
        tr.addEventListener('click', (e) => {
          // Ignorar clicks em checkbox e dropdown
          if (e.target.closest('input[type="checkbox"]') || e.target.closest('.dropdown')) return;
          PalletDetail.open(parseInt(tr.dataset.nfId));
        });
      });

      // Checkboxes
      body.querySelectorAll('.pu-row-check').forEach(cb => {
        cb.addEventListener('change', () => {
          const id = parseInt(cb.dataset.creditoId);
          if (cb.checked) this._selectedIds.add(id);
          else this._selectedIds.delete(id);
        });
      });
    },

    _renderRow(item) {
      const empresaClass = (item.empresa || '').toLowerCase();
      const tipoClass = (item.tipo_destinatario || '').toLowerCase();
      const saldoClass = item.qtd_saldo > 0 ? 'pu-saldo--positivo' : 'pu-saldo--zero';
      const vctoClass = item.vencido ? 'pu-vcto--vencido' : (item.prestes_a_vencer ? 'pu-vcto--prestes' : '');
      const statusClass = (item.status || '').toLowerCase();

      return `<tr data-nf-id="${item.id}" data-credito-id="${item.credito_id || ''}">
        <td class="text-center">
          ${item.credito_id ? `<input type="checkbox" class="pu-row-check" data-credito-id="${item.credito_id}" data-saldo="${item.qtd_saldo}">` : ''}
        </td>
        <td>
          <strong>${escapeHtml(item.numero_nf)}</strong>
          <span class="pu-badge-status pu-badge-status--${statusClass}">${item.status}</span>
        </td>
        <td>${item.data_emissao}</td>
        <td><span class="pu-badge-empresa pu-badge-empresa--${empresaClass}">${item.empresa}</span></td>
        <td title="${formatCnpj(item.cnpj_destinatario)}">${escapeHtml(item.nome_destinatario).substring(0, 25)}</td>
        <td><span class="pu-badge-tipo pu-badge-tipo--${tipoClass}">${item.tipo_destinatario === 'TRANSPORTADORA' ? 'TRANS' : 'CLI'}</span></td>
        <td class="text-end">${item.quantidade}</td>
        <td class="text-end ${saldoClass}">${item.qtd_saldo}</td>
        <td class="text-center">
          <div class="pu-progress" title="Pallets: ${item.dom_a_resolvida} resolvidos de ${item.dom_a_original}">
            <span class="pu-progress__qty">${item.dom_a_resolvida}/${item.dom_a_original}</span>
            <span class="pu-progress__pct">${item.dom_a_pct}%</span>
            <div class="pu-progress__bar"><div class="pu-progress__fill pu-progress__fill--a" style="width:${item.dom_a_pct}%"></div></div>
          </div>
        </td>
        <td class="text-center">
          <div class="pu-progress" title="Pend. NF: ${item.dom_b_resolvida} resolvidos de ${item.dom_b_total}">
            <span class="pu-progress__qty">${item.dom_b_resolvida}/${item.dom_b_total}</span>
            <span class="pu-progress__pct">${item.dom_b_pct}%</span>
            <div class="pu-progress__bar"><div class="pu-progress__fill pu-progress__fill--b" style="width:${item.dom_b_pct}%"></div></div>
          </div>
        </td>
        <td class="${vctoClass}">${item.data_vencimento}${item.vencido ? ' <i class="fas fa-exclamation-circle"></i>' : ''}</td>
        <td class="text-center">
          <span class="pu-docs-badge">
            <i class="fas fa-file-alt"></i> ${item.docs_recebidos}/${item.total_docs}
          </span>
        </td>
        <td class="text-center">
          <div class="dropdown pu-acoes-dropdown">
            <button class="btn btn-outline-secondary pu-acoes-btn dropdown-toggle" type="button" data-bs-toggle="dropdown" onclick="event.stopPropagation()">
              <i class="fas fa-ellipsis-v"></i>
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              ${item.credito_id && item.qtd_saldo > 0 ? `
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openBaixa(${item.credito_id}, ${item.qtd_saldo}); return false;"><i class="fas fa-arrow-down me-2"></i>Baixa</a></li>
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openRecebimento(${item.credito_id}, ${item.qtd_saldo}); return false;"><i class="fas fa-hand-holding me-2"></i>Recebimento</a></li>
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openSubstituicao(${item.credito_id}, ${item.qtd_saldo}, '${escapeHtml(item.nome_destinatario)}'); return false;"><i class="fas fa-exchange-alt me-2"></i>Substituicao</a></li>
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openVendaSingle(${item.credito_id}, ${item.qtd_saldo}); return false;"><i class="fas fa-shopping-cart me-2"></i>Venda</a></li>
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openDocumento(${item.credito_id}); return false;"><i class="fas fa-file-alt me-2"></i>Documento</a></li>
              ` : ''}
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openDevolucao(${item.id}, '${escapeHtml(item.numero_nf)}'); return false;"><i class="fas fa-undo me-2"></i>Vincular Devolucao</a></li>
              <li><a class="dropdown-item" href="#" onclick="PalletModals.openRecusa(${item.id}); return false;"><i class="fas fa-ban me-2"></i>Recusa</a></li>
              ${item.status !== 'CANCELADA' ? `
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item text-danger" href="#" onclick="PalletModals.openCancelarNf(${item.id}, '${escapeHtml(item.numero_nf)}'); return false;"><i class="fas fa-times-circle me-2"></i>Cancelar NF</a></li>
              ` : ''}
            </ul>
          </div>
        </td>
      </tr>`;
    },

    _renderPagination(dados) {
      const info = document.getElementById('paginacaoInfo');
      const nav = document.getElementById('paginacaoNav');
      const inicio = (dados.pagina - 1) * dados.por_pagina + 1;
      const fim = Math.min(dados.pagina * dados.por_pagina, dados.total);
      info.textContent = `${inicio}-${fim} de ${dados.total}`;

      let html = '';
      // Anterior
      html += `<li class="page-item ${!dados.tem_anterior ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${dados.pagina - 1}">&laquo;</a></li>`;

      // Paginas
      const maxPages = 5;
      let start = Math.max(1, dados.pagina - 2);
      let end = Math.min(dados.paginas, start + maxPages - 1);
      if (end - start < maxPages - 1) start = Math.max(1, end - maxPages + 1);

      for (let i = start; i <= end; i++) {
        html += `<li class="page-item ${i === dados.pagina ? 'active' : ''}">
          <a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
      }

      // Proximo
      html += `<li class="page-item ${!dados.tem_proximo ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${dados.pagina + 1}">&raquo;</a></li>`;

      nav.innerHTML = html;

      // Event listeners
      nav.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const page = parseInt(link.dataset.page);
          if (page > 0 && page <= dados.paginas) {
            PalletTable.load(page);
          }
        });
      });
    },

    async _loadContadores() {
      try {
        const { dados } = await apiFetch(`${API_BASE}/api/contadores`);
        document.getElementById('tabCountVisao').textContent = dados.visao_geral;
        document.getElementById('tabCountVencendo').textContent = dados.vencendo;
        document.getElementById('tabCountSugestoes').textContent = dados.sugestoes;
        document.getElementById('tabCountHistorico').textContent = dados.historico;
      } catch (e) { /* ignore */ }
    },

    async reloadRow(nfId) {
      try {
        const { dados } = await apiFetch(`${API_BASE}/api/tabela/row/${nfId}`);
        const tr = document.querySelector(`tr[data-nf-id="${nfId}"]`);
        if (tr) {
          const temp = document.createElement('tbody');
          temp.innerHTML = this._renderRow(dados);
          tr.replaceWith(temp.firstElementChild);
        }
      } catch (e) {
        // Fallback: recarregar tabela inteira
        this.load(this._currentPage);
      }
    },

    getSelectedCreditos() {
      const result = [];
      this._selectedIds.forEach(creditoId => {
        const cb = document.querySelector(`.pu-row-check[data-credito-id="${creditoId}"]`);
        if (cb) {
          result.push({
            credito_id: creditoId,
            quantidade: parseInt(cb.dataset.saldo) || 0
          });
        }
      });
      return result;
    }
  };

  // ========================================================================
  // MODULE: PalletDetail (Offcanvas)
  // ========================================================================

  const PalletDetail = {
    _offcanvas: null,
    _currentNfId: null,

    init() {
      this._offcanvas = new bootstrap.Offcanvas(document.getElementById('painelLateral'));
    },

    async open(nfId) {
      this._currentNfId = nfId;
      const body = document.getElementById('painelLateralBody');
      body.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">Carregando...</p></div>';
      this._offcanvas.show();

      try {
        const { dados } = await apiFetch(`${API_BASE}/api/nf/${nfId}/completo`);
        body.innerHTML = this._render(dados);
        this._bindActions(body, dados);
      } catch (err) {
        body.innerHTML = `<div class="pu-empty"><i class="fas fa-exclamation-circle"></i><div class="pu-empty__text">Erro ao carregar detalhes</div></div>`;
      }
    },

    _render(d) {
      const nf = d.nf;
      const resumo = d.resumo;
      let html = '';

      // Cabecalho
      html += `<div class="pu-detail-section">
        <div class="pu-detail-section__title">NF de Remessa</div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">NF</span><span class="pu-detail-field__value">${escapeHtml(nf.numero_nf)}</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Empresa</span><span class="pu-detail-field__value">${nf.empresa}</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Emissao</span><span class="pu-detail-field__value">${formatDateBr(nf.data_emissao)}</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Destinatario</span><span class="pu-detail-field__value">${escapeHtml(nf.nome_destinatario)}</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">CNPJ</span><span class="pu-detail-field__value">${formatCnpj(nf.cnpj_destinatario)}</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Quantidade</span><span class="pu-detail-field__value">${nf.quantidade}</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Status</span><span class="pu-detail-field__value">${nf.status}</span></div>
      </div>`;

      // Resumo Dom.A e Dom.B
      html += `<div class="pu-detail-section">
        <div class="pu-detail-section__title">Resumo</div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Pallets (Credito)</span><span class="pu-detail-field__value">${resumo.dom_a.qtd_resolvida}/${resumo.dom_a.qtd_original} (${resumo.dom_a.percentual}%)</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Pend. NF</span><span class="pu-detail-field__value">${resumo.dom_b.qtd_resolvida}/${resumo.dom_b.qtd_total} (${resumo.dom_b.percentual}%)</span></div>
        <div class="pu-detail-field"><span class="pu-detail-field__label">Documentos</span><span class="pu-detail-field__value">${resumo.docs_recebidos}/${resumo.total_documentos} recebidos</span></div>
      </div>`;

      // Creditos + Documentos
      if (d.creditos && d.creditos.length) {
        d.creditos.forEach(c => {
          html += `<div class="pu-detail-section">
            <div class="pu-detail-section__title">Credito #${c.id} — ${c.status}</div>
            <div class="pu-detail-field"><span class="pu-detail-field__label">Saldo</span><span class="pu-detail-field__value">${c.qtd_saldo}/${c.qtd_original}</span></div>
            <div class="pu-detail-field"><span class="pu-detail-field__label">Responsavel</span><span class="pu-detail-field__value">${escapeHtml(c.nome_responsavel)}</span></div>
            <div class="pu-detail-field"><span class="pu-detail-field__label">Vencimento</span><span class="pu-detail-field__value ${c.vencido ? 'pu-vcto--vencido' : ''}">${c.data_vencimento || 'N/D'}</span></div>`;

          // Documentos
          if (c.documentos && c.documentos.length) {
            html += '<div class="mt-2"><small class="text-muted fw-bold">Documentos:</small>';
            c.documentos.forEach(doc => {
              html += `<div class="d-flex justify-content-between align-items-center py-1 border-bottom" style="font-size:0.78rem;">
                <span>${doc.tipo_display} — ${doc.quantidade} pallet(s)</span>
                ${!doc.recebido ?
                  `<button class="btn btn-success btn-sm py-0 px-2" style="font-size:0.7rem;" data-action="receber-doc" data-doc-id="${doc.id}">Receber</button>` :
                  `<span class="text-success"><i class="fas fa-check"></i> Recebido</span>`}
              </div>`;
            });
            html += '</div>';
          }

          // Solucoes Dom.A
          if (c.solucoes && c.solucoes.length) {
            html += '<div class="mt-2"><small class="text-muted fw-bold">Solucoes Pallets:</small>';
            html += '<ul class="pu-timeline">';
            c.solucoes.forEach(s => {
              const icon = { BAIXA: 'fa-arrow-down', VENDA: 'fa-shopping-cart', RECEBIMENTO: 'fa-hand-holding', SUBSTITUICAO: 'fa-exchange-alt' }[s.tipo] || 'fa-check';
              html += `<li class="pu-timeline__item">
                <div class="pu-timeline__icon"><i class="fas ${icon}"></i></div>
                <div class="pu-timeline__body">
                  <div class="pu-timeline__title">${s.tipo_display} — ${s.quantidade} pallet(s)</div>
                  <div class="pu-timeline__meta">${formatDateBr(s.criado_em)} por ${escapeHtml(s.criado_por || '')}</div>
                </div>
              </li>`;
            });
            html += '</ul></div>';
          }

          // Acoes rapidas
          if (c.qtd_saldo > 0) {
            html += `<div class="pu-quick-actions">
              <button class="btn btn-outline-primary btn-sm" onclick="PalletModals.openBaixa(${c.id}, ${c.qtd_saldo})"><i class="fas fa-arrow-down"></i> Baixa</button>
              <button class="btn btn-outline-success btn-sm" onclick="PalletModals.openRecebimento(${c.id}, ${c.qtd_saldo})"><i class="fas fa-hand-holding"></i> Recebimento</button>
              <button class="btn btn-outline-warning btn-sm" onclick="PalletModals.openVendaSingle(${c.id}, ${c.qtd_saldo})"><i class="fas fa-shopping-cart"></i> Venda</button>
              <button class="btn btn-outline-secondary btn-sm" onclick="PalletModals.openDocumento(${c.id})"><i class="fas fa-file-alt"></i> Documento</button>
            </div>`;
          }

          html += '</div>';
        });
      }

      // Sugestoes pendentes
      if (d.sugestoes_pendentes && d.sugestoes_pendentes.length) {
        html += '<div class="pu-detail-section"><div class="pu-detail-section__title">Sugestoes Pendentes</div>';
        d.sugestoes_pendentes.forEach(s => {
          html += `<div class="pu-sugestao">
            <div><strong>${s.tipo_display}</strong> — ${s.quantidade} pallet(s)</div>
            <div style="font-size:0.75rem;">NF: ${escapeHtml(s.numero_nf_solucao || '-')} | ${escapeHtml(s.nome_emitente || '-')}</div>
            <div class="pu-sugestao__actions">
              <button class="btn btn-success btn-sm" data-action="confirmar-sugestao" data-solucao-id="${s.id}"><i class="fas fa-check"></i> Confirmar</button>
              <button class="btn btn-outline-danger btn-sm" data-action="rejeitar-sugestao" data-solucao-id="${s.id}"><i class="fas fa-times"></i> Rejeitar</button>
            </div>
          </div>`;
        });
        html += '</div>';
      }

      // Solucoes Dom.B
      if (d.solucoes_nf && d.solucoes_nf.length) {
        html += '<div class="pu-detail-section"><div class="pu-detail-section__title">Solucoes Pend. NF</div>';
        html += '<ul class="pu-timeline">';
        d.solucoes_nf.forEach(s => {
          const icon = { DEVOLUCAO: 'fa-undo', RECUSA: 'fa-ban', CANCELAMENTO: 'fa-times', NOTA_CREDITO: 'fa-receipt' }[s.tipo] || 'fa-check';
          html += `<li class="pu-timeline__item">
            <div class="pu-timeline__icon"><i class="fas ${icon}"></i></div>
            <div class="pu-timeline__body">
              <div class="pu-timeline__title">${s.tipo_display} — ${s.quantidade} pallet(s)</div>
              <div class="pu-timeline__meta">${s.status_display} | ${escapeHtml(s.criado_por || '')} | ${formatDateBr(s.criado_em)}</div>
            </div>
          </li>`;
        });
        html += '</ul></div>';
      }

      return html;
    },

    _bindActions(body, dados) {
      // Receber documento (inline)
      body.querySelectorAll('[data-action="receber-doc"]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const docId = btn.dataset.docId;
          btn.disabled = true;
          btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
          try {
            await apiFetch(`${API_BASE}/api/acoes/documento/${docId}/receber`, { method: 'POST' });
            showToast('Documento recebido com sucesso');
            this.open(this._currentNfId); // Reload detail
            PalletKPIs.load();
          } catch (err) {
            showToast(err.message, 'error');
            btn.disabled = false;
            btn.innerHTML = 'Receber';
          }
        });
      });

      // Confirmar sugestao (inline)
      body.querySelectorAll('[data-action="confirmar-sugestao"]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const solId = btn.dataset.solucaoId;
          btn.disabled = true;
          try {
            await apiFetch(`${API_BASE}/api/acoes/confirmar-sugestao/${solId}`, { method: 'POST' });
            showToast('Sugestao confirmada');
            this.open(this._currentNfId);
            PalletKPIs.load();
            PalletTable.reloadRow(this._currentNfId);
          } catch (err) {
            showToast(err.message, 'error');
            btn.disabled = false;
          }
        });
      });

      // Rejeitar sugestao (abre modal)
      body.querySelectorAll('[data-action="rejeitar-sugestao"]').forEach(btn => {
        btn.addEventListener('click', () => {
          PalletModals.openRejeitar(parseInt(btn.dataset.solucaoId));
        });
      });
    }
  };

  // ========================================================================
  // MODULE: PalletModals
  // ========================================================================

  const PalletModals = {
    init() {
      // Baixa
      document.getElementById('btnSalvarBaixa').addEventListener('click', () => this._submitBaixa());
      // Recebimento
      document.getElementById('btnSalvarRecebimento').addEventListener('click', () => this._submitRecebimento());
      // Venda
      document.getElementById('btnSalvarVenda').addEventListener('click', () => this._submitVenda());
      // Substituicao
      document.getElementById('btnSalvarSubstituicao').addEventListener('click', () => this._submitSubstituicao());
      // Documento
      document.getElementById('btnSalvarDocumento').addEventListener('click', () => this._submitDocumento());
      // Devolucao
      document.getElementById('btnSalvarDevolucao').addEventListener('click', () => this._submitDevolucao());
      document.getElementById('btnDevolAddVinc').addEventListener('click', () => this._addDevolVinculacao());
      // Recusa
      document.getElementById('btnSalvarRecusa').addEventListener('click', () => this._submitRecusa());
      // Rejeitar
      document.getElementById('btnSalvarRejeicao').addEventListener('click', () => this._submitRejeitar());
      // Cancelar NF
      document.getElementById('btnConfirmarCancelamento').addEventListener('click', () => this._submitCancelarNf());
    },

    // Abrir modais
    openBaixa(creditoId, saldo) {
      document.getElementById('baixaCreditoId').value = creditoId;
      document.getElementById('baixaSaldo').textContent = saldo;
      document.getElementById('baixaQuantidade').value = '';
      document.getElementById('baixaQuantidade').max = saldo;
      document.getElementById('baixaMotivo').value = '';
      document.getElementById('baixaConfirmado').checked = false;
      document.getElementById('baixaObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalBaixa')).show();
    },

    openRecebimento(creditoId, saldo) {
      document.getElementById('recebCreditoId').value = creditoId;
      document.getElementById('recebSaldo').textContent = saldo;
      document.getElementById('recebQuantidade').value = '';
      document.getElementById('recebQuantidade').max = saldo;
      document.getElementById('recebData').value = new Date().toISOString().split('T')[0];
      document.getElementById('recebLocal').value = '';
      document.getElementById('recebObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalRecebimento')).show();
    },

    openVenda() {
      const creditos = PalletTable.getSelectedCreditos();
      const lista = document.getElementById('vendaCreditosLista');
      if (!creditos.length) {
        lista.innerHTML = '<p class="text-warning"><i class="fas fa-exclamation-triangle"></i> Selecione creditos na tabela antes.</p>';
      } else {
        lista.innerHTML = creditos.map(c => `
          <div class="d-flex justify-content-between align-items-center py-1 border-bottom" style="font-size:0.82rem;">
            <span>Credito #${c.credito_id}</span>
            <input type="number" class="form-control form-control-sm" style="width:80px;" value="${c.quantidade}" min="1" max="${c.quantidade}" data-credito-venda="${c.credito_id}">
          </div>
        `).join('');
      }
      document.getElementById('vendaNf').value = '';
      document.getElementById('vendaData').value = new Date().toISOString().split('T')[0];
      document.getElementById('vendaValor').value = '35.00';
      document.getElementById('vendaCnpj').value = '';
      document.getElementById('vendaNome').value = '';
      document.getElementById('vendaObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalVenda')).show();
    },

    openVendaSingle(creditoId, saldo) {
      const lista = document.getElementById('vendaCreditosLista');
      lista.innerHTML = `<div class="d-flex justify-content-between align-items-center py-1 border-bottom" style="font-size:0.82rem;">
        <span>Credito #${creditoId}</span>
        <input type="number" class="form-control form-control-sm" style="width:80px;" value="${saldo}" min="1" max="${saldo}" data-credito-venda="${creditoId}">
      </div>`;
      document.getElementById('vendaNf').value = '';
      document.getElementById('vendaData').value = new Date().toISOString().split('T')[0];
      document.getElementById('vendaValor').value = '35.00';
      document.getElementById('vendaCnpj').value = '';
      document.getElementById('vendaNome').value = '';
      document.getElementById('vendaObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalVenda')).show();
    },

    openSubstituicao(creditoId, saldo, nomeResponsavel) {
      document.getElementById('substOrigemId').value = creditoId;
      document.getElementById('substOrigemInfo').value = `#${creditoId} - ${nomeResponsavel}`;
      document.getElementById('substSaldo').textContent = saldo;
      document.getElementById('substQuantidade').value = '';
      document.getElementById('substQuantidade').max = saldo;
      document.getElementById('substDestinoId').value = '';
      document.getElementById('substMotivo').value = '';
      document.getElementById('substObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalSubstituicao')).show();
    },

    openDocumento(creditoId) {
      document.getElementById('docCreditoId').value = creditoId;
      document.getElementById('docTipo').value = 'CANHOTO';
      document.getElementById('docQuantidade').value = '';
      document.getElementById('docNumero').value = '';
      document.getElementById('docEmissao').value = '';
      document.getElementById('docValidade').value = '';
      document.getElementById('docObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalDocumento')).show();
    },

    openDevolucao(nfId, numeroNf) {
      this._devolVinculacoes = {};
      document.getElementById('devolNf').value = '';
      document.getElementById('devolData').value = new Date().toISOString().split('T')[0];
      document.getElementById('devolQtdTotal').value = '';
      document.getElementById('devolCnpj').value = '';
      document.getElementById('devolNome').value = '';
      document.getElementById('devolVinculacoes').innerHTML = '<p class="text-muted">Adicione NFs de remessa para distribuir a quantidade</p>';
      // Pre-adicionar a NF remessa atual
      document.getElementById('devolAddNfId').value = nfId;
      document.getElementById('devolAddQtd').value = '';
      new bootstrap.Modal(document.getElementById('modalDevolucao')).show();
    },

    openRecusa(nfId) {
      document.getElementById('recusaNfId').value = nfId;
      document.getElementById('recusaQuantidade').value = '';
      document.getElementById('recusaMotivo').value = '';
      document.getElementById('recusaObservacao').value = '';
      new bootstrap.Modal(document.getElementById('modalRecusa')).show();
    },

    openRejeitar(solucaoId) {
      document.getElementById('rejeitarSolucaoId').value = solucaoId;
      document.getElementById('rejeitarMotivo').value = '';
      new bootstrap.Modal(document.getElementById('modalRejeitar')).show();
    },

    openCancelarNf(nfId, numeroNf) {
      document.getElementById('cancelarNfId').value = nfId;
      document.getElementById('cancelarNfInfo').value = `NF ${numeroNf} (ID: ${nfId})`;
      document.getElementById('cancelarMotivo').value = '';
      new bootstrap.Modal(document.getElementById('modalCancelarNf')).show();
    },

    // Submits
    async _submitBaixa() {
      const creditoId = parseInt(document.getElementById('baixaCreditoId').value);
      const payload = {
        credito_id: creditoId,
        quantidade: parseInt(document.getElementById('baixaQuantidade').value),
        motivo: document.getElementById('baixaMotivo').value,
        confirmado_cliente: document.getElementById('baixaConfirmado').checked,
        observacao: document.getElementById('baixaObservacao').value || null
      };
      await this._submit('baixa', payload, 'modalBaixa', creditoId);
    },

    async _submitRecebimento() {
      const creditoId = parseInt(document.getElementById('recebCreditoId').value);
      const payload = {
        credito_id: creditoId,
        quantidade: parseInt(document.getElementById('recebQuantidade').value),
        data_recebimento: document.getElementById('recebData').value,
        local_recebimento: document.getElementById('recebLocal').value,
        observacao: document.getElementById('recebObservacao').value || null
      };
      await this._submit('recebimento', payload, 'modalRecebimento', creditoId);
    },

    async _submitVenda() {
      const creditos = [];
      document.querySelectorAll('[data-credito-venda]').forEach(input => {
        creditos.push({
          credito_id: parseInt(input.dataset.creditoVenda),
          quantidade: parseInt(input.value)
        });
      });
      const payload = {
        nf_venda: document.getElementById('vendaNf').value,
        creditos: creditos,
        data_venda: document.getElementById('vendaData').value,
        valor_unitario: parseFloat(document.getElementById('vendaValor').value),
        cnpj_comprador: document.getElementById('vendaCnpj').value,
        nome_comprador: document.getElementById('vendaNome').value,
        observacao: document.getElementById('vendaObservacao').value || null
      };
      await this._submit('venda', payload, 'modalVenda');
    },

    async _submitSubstituicao() {
      const payload = {
        credito_origem_id: parseInt(document.getElementById('substOrigemId').value),
        credito_destino_id: parseInt(document.getElementById('substDestinoId').value),
        quantidade: parseInt(document.getElementById('substQuantidade').value),
        motivo: document.getElementById('substMotivo').value,
        observacao: document.getElementById('substObservacao').value || null
      };
      await this._submit('substituicao', payload, 'modalSubstituicao');
    },

    async _submitDocumento() {
      const payload = {
        credito_id: parseInt(document.getElementById('docCreditoId').value),
        tipo: document.getElementById('docTipo').value,
        quantidade: parseInt(document.getElementById('docQuantidade').value),
        numero_documento: document.getElementById('docNumero').value || null,
        data_emissao: document.getElementById('docEmissao').value || null,
        data_validade: document.getElementById('docValidade').value || null,
        observacao: document.getElementById('docObservacao').value || null
      };
      await this._submit('documento', payload, 'modalDocumento');
    },

    _devolVinculacoes: {},

    _addDevolVinculacao() {
      const nfId = parseInt(document.getElementById('devolAddNfId').value);
      const qtd = parseInt(document.getElementById('devolAddQtd').value);
      if (!nfId || !qtd) return;

      this._devolVinculacoes[nfId] = qtd;
      const container = document.getElementById('devolVinculacoes');
      let html = '';
      for (const [id, q] of Object.entries(this._devolVinculacoes)) {
        html += `<div class="d-flex justify-content-between py-1 border-bottom" style="font-size:0.82rem;">
          <span>NF Remessa #${id}: ${q} pallet(s)</span>
          <button class="btn btn-sm btn-outline-danger py-0" onclick="delete PalletModals._devolVinculacoes[${id}]; PalletModals._addDevolVinculacao();"><i class="fas fa-times"></i></button>
        </div>`;
      }
      container.innerHTML = html || '<p class="text-muted">Nenhuma vinculacao adicionada</p>';
      document.getElementById('devolAddNfId').value = '';
      document.getElementById('devolAddQtd').value = '';
    },

    async _submitDevolucao() {
      const payload = {
        nf_devolucao: {
          numero_nf: document.getElementById('devolNf').value,
          data_nf: document.getElementById('devolData').value,
          quantidade: parseInt(document.getElementById('devolQtdTotal').value),
          cnpj_emitente: document.getElementById('devolCnpj').value,
          nome_emitente: document.getElementById('devolNome').value
        },
        vinculacoes: this._devolVinculacoes
      };
      await this._submit('vincular-devolucao', payload, 'modalDevolucao');
      this._devolVinculacoes = {};
    },

    async _submitRecusa() {
      const payload = {
        nf_remessa_id: parseInt(document.getElementById('recusaNfId').value),
        quantidade: parseInt(document.getElementById('recusaQuantidade').value),
        motivo_recusa: document.getElementById('recusaMotivo').value,
        observacao: document.getElementById('recusaObservacao').value || null
      };
      await this._submit('registrar-recusa', payload, 'modalRecusa');
    },

    async _submitRejeitar() {
      const solucaoId = parseInt(document.getElementById('rejeitarSolucaoId').value);
      const payload = { motivo: document.getElementById('rejeitarMotivo').value };
      try {
        const result = await apiFetch(`${API_BASE}/api/acoes/rejeitar-sugestao/${solucaoId}`, {
          method: 'POST', body: payload
        });
        showToast(result.mensagem);
        bootstrap.Modal.getInstance(document.getElementById('modalRejeitar'))?.hide();
        PalletKPIs.load();
        if (PalletDetail._currentNfId) PalletDetail.open(PalletDetail._currentNfId);
      } catch (err) {
        showToast(err.message, 'error');
      }
    },

    async _submitCancelarNf() {
      const nfId = parseInt(document.getElementById('cancelarNfId').value);
      const payload = { motivo: document.getElementById('cancelarMotivo').value };
      try {
        const result = await apiFetch(`${API_BASE}/api/acoes/cancelar-nf/${nfId}`, {
          method: 'POST', body: payload
        });
        showToast(result.mensagem);
        bootstrap.Modal.getInstance(document.getElementById('modalCancelarNf'))?.hide();
        PalletKPIs.load();
        PalletTable.reloadRow(nfId);
      } catch (err) {
        showToast(err.message, 'error');
      }
    },

    // Submit generico: POST, fechar modal, atualizar UI
    async _submit(action, payload, modalId, relatedCreditoId) {
      try {
        const result = await apiFetch(`${API_BASE}/api/acoes/${action}`, {
          method: 'POST', body: payload
        });
        showToast(result.mensagem);
        bootstrap.Modal.getInstance(document.getElementById(modalId))?.hide();

        // Atualizar UI
        PalletKPIs.load();
        const nfId = result.dados?.nf_remessa_id;
        if (nfId) {
          PalletTable.reloadRow(nfId);
          if (PalletDetail._currentNfId === nfId) PalletDetail.open(nfId);
        } else {
          PalletTable.load(PalletTable._currentPage);
        }
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  };

  // Expor globalmente para onclick nos templates
  window.PalletModals = PalletModals;

  // ========================================================================
  // MODULE: PalletSync
  // ========================================================================

  const PalletSync = {
    init() {
      document.getElementById('btnSyncOdoo').addEventListener('click', () => this._syncOdoo());
      document.getElementById('btnProcessarDfe').addEventListener('click', () => this._processarDfe());
      document.getElementById('btnExportar').addEventListener('click', () => this._exportarXlsx());
      document.getElementById('btnVendaLote').addEventListener('click', () => PalletModals.openVenda());
    },

    _exportarXlsx() {
      const filtros = PalletFilters.getAll();
      const params = new URLSearchParams(filtros);
      params.set('ordenar_por', PalletTable._sortBy);
      params.set('ordem', PalletTable._sortOrder);
      // Abre download em nova aba
      window.open(`${API_BASE}/api/exportar?${params}`, '_blank');
    },

    async _syncOdoo() {
      const btn = document.getElementById('btnSyncOdoo');
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sincronizando...';
      try {
        const result = await apiFetch(`${API_BASE}/api/acoes/sync-odoo`, { method: 'POST' });
        showToast(result.mensagem);
        PalletKPIs.load();
        PalletTable.load(1);
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sync-alt"></i> Sync Odoo';
      }
    },

    async _processarDfe() {
      const btn = document.getElementById('btnProcessarDfe');
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
      try {
        const result = await apiFetch(`${API_BASE}/api/acoes/processar-dfe`, { method: 'POST' });
        showToast(result.mensagem);
        PalletKPIs.load();
        PalletTable.load(1);
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-file-invoice"></i> Processar DFe';
      }
    }
  };

  // ========================================================================
  // INIT
  // ========================================================================

  document.addEventListener('DOMContentLoaded', () => {
    PalletFilters.init();
    PalletTable.init();
    PalletDetail.init();
    PalletModals.init();
    PalletSync.init();

    // Carga inicial
    PalletKPIs.load();
    PalletTable.load(1);

    // Auto-refresh KPIs
    setInterval(() => PalletKPIs.load(), REFRESH_INTERVAL);
  });

})();
