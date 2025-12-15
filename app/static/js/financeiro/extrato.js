/**
 * Sistema Financeiro - JavaScript
 * ================================
 * Gerencia interações das telas financeiras
 * Suporte a Dark/Light Mode (sincronizado com sistema global)
 */

// =============================================================================
// GERENCIADOR DE TEMA (Sincronizado com NacomTheme global)
// =============================================================================

const ThemeManager = {
    STORAGE_KEY: 'nacom-theme', // Usa mesma chave do sistema global
    LIGHT: 'light',
    DARK: 'dark',

    init() {
        // Sincroniza com o tema global já aplicado pelo theme-manager.js
        // Se NacomTheme existir, usa ele como fonte de verdade
        if (window.NacomTheme) {
            this.syncWithGlobal();
            // Escuta mudanças do tema global
            document.addEventListener('themechange', () => this.syncWithGlobal());
        } else {
            // Fallback se theme-manager.js não carregou ainda
            const savedTheme = localStorage.getItem(this.STORAGE_KEY);
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (prefersDark ? this.DARK : this.LIGHT);
            this.apply(theme);
        }

        // Listener para mudança de preferência do sistema
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.STORAGE_KEY)) {
                this.apply(e.matches ? this.DARK : this.LIGHT);
            }
        });
    },

    syncWithGlobal() {
        // Sincroniza com o estado do NacomTheme
        if (window.NacomTheme) {
            this.updateToggleIcons();
        }
    },

    apply(theme) {
        // Aplica ambos os atributos para compatibilidade
        document.documentElement.setAttribute('data-bs-theme', theme);
        document.documentElement.setAttribute('data-theme', theme);
        this.updateToggleIcons();
    },

    toggle() {
        // Se NacomTheme existe, delega para ele
        if (window.NacomTheme) {
            return window.NacomTheme.toggle();
        }

        // Fallback
        const currentTheme = document.documentElement.getAttribute('data-theme') ||
                            document.documentElement.getAttribute('data-bs-theme') || 'dark';
        const newTheme = currentTheme === 'light' ? this.DARK : this.LIGHT;

        localStorage.setItem(this.STORAGE_KEY, newTheme);
        this.apply(newTheme);

        return newTheme;
    },

    updateToggleIcons() {
        const currentTheme = document.documentElement.getAttribute('data-theme') ||
                            document.documentElement.getAttribute('data-bs-theme') || 'dark';
        const isLight = currentTheme === 'light';

        document.querySelectorAll('.theme-toggle__icon--light').forEach(el => {
            el.style.display = isLight ? 'none' : 'inline';
        });
        document.querySelectorAll('.theme-toggle__icon--dark').forEach(el => {
            el.style.display = isLight ? 'inline' : 'none';
        });
    },

    getCurrent() {
        const theme = document.documentElement.getAttribute('data-theme') ||
                     document.documentElement.getAttribute('data-bs-theme') || 'dark';
        return theme === 'light' ? this.LIGHT : this.DARK;
    }
};

// Inicializar tema após um pequeno delay para garantir que NacomTheme carregou
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
} else {
    ThemeManager.init();
}

// Função global para toggle de tema (compatibilidade)
function toggleTheme() {
    return ThemeManager.toggle();
}

// =============================================================================
// ESTADO GLOBAL
// =============================================================================

const ExtratoApp = {
    // Estado
    selectedLotes: new Set(),
    selectedStatements: new Set(),
    selectedRecebimentos: new Set(),
    selectedPagamentos: new Set(),
    statementsData: [],
    statementsRecebimentos: [],
    statementsPagamentos: [],
    journalsData: [],

    // Elementos (serão populados no init)
    elements: {},

    // Configuração
    config: {
        apiBaseUrl: '/financeiro/extrato',
        debounceDelay: 300
    }
};

// =============================================================================
// INICIALIZAÇÃO
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    ExtratoApp.init();
});

ExtratoApp.init = function() {
    this.cacheElements();
    this.bindEvents();
    this.loadStatements();
    this.initFilters();
};

ExtratoApp.cacheElements = function() {
    this.elements = {
        // Seções
        lotesSection: document.getElementById('lotesSection'),
        pendentesSection: document.getElementById('pendentesSection'),

        // Tabelas
        lotesTable: document.getElementById('lotesTableBody'),
        pendentesTable: document.getElementById('pendentesTableBody'),

        // Checkboxes
        selectAllLotes: document.getElementById('selectAllLotes'),
        selectAllPendentes: document.getElementById('selectAllPendentes'),

        // Badges
        badgePendentesTotal: document.getElementById('badgePendentesTotal'),

        // Bulk actions
        bulkActionsBar: document.getElementById('bulkActionsBar'),
        bulkCount: document.getElementById('bulkCount'),
        bulkText: document.getElementById('bulkText'),

        // Filtros
        filterForm: document.getElementById('filterForm'),
        filterDataDe: document.getElementById('filterDataDe'),
        filterDataAte: document.getElementById('filterDataAte'),
        filterStatus: document.getElementById('filterStatus'),
        filterJournal: document.getElementById('filterJournal'),
        filterTipo: document.getElementById('filterTipo'),

        // Paginação
        perPageSelect: document.getElementById('perPageSelect')
    };
};

ExtratoApp.bindEvents = function() {
    // Toggle de seções colapsáveis
    document.querySelectorAll('.extrato-section__header').forEach(header => {
        header.addEventListener('click', function() {
            const section = this.closest('.extrato-section');
            section.classList.toggle('collapsed');
        });
    });

    // Select all lotes
    if (this.elements.selectAllLotes) {
        this.elements.selectAllLotes.addEventListener('change', (e) => {
            this.toggleAllLotes(e.target.checked);
        });
    }

    // Select all pendentes (unificado)
    if (this.elements.selectAllPendentes) {
        this.elements.selectAllPendentes.addEventListener('change', (e) => {
            this.toggleAllPendentes(e.target.checked);
        });
    }

    // Filtros - submit no change
    const filterInputs = document.querySelectorAll('.filter-group__input, .filter-group__select');
    filterInputs.forEach(input => {
        input.addEventListener('change', () => {
            this.submitFilters();
        });
    });

    // Per page change
    if (this.elements.perPageSelect) {
        this.elements.perPageSelect.addEventListener('change', () => {
            this.submitFilters();
        });
    }

    // Quick filters - status
    document.querySelectorAll('.quick-filter[data-status]').forEach(btn => {
        btn.addEventListener('click', function() {
            const status = this.dataset.status;
            ExtratoApp.applyQuickFilter('status', status);
        });
    });

    // Quick filters - tipo
    document.querySelectorAll('.quick-filter[data-tipo]').forEach(btn => {
        btn.addEventListener('click', function() {
            const tipo = this.dataset.tipo;
            ExtratoApp.applyQuickFilter('tipo', tipo);
        });
    });
};

// =============================================================================
// FILTROS
// =============================================================================

ExtratoApp.initFilters = function() {
    // Marcar quick filter ativo baseado na URL
    const urlParams = new URLSearchParams(window.location.search);
    const currentStatus = urlParams.get('status') || 'all';
    const currentTipo = urlParams.get('tipo') || 'all';

    document.querySelectorAll('.quick-filter[data-status]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === currentStatus);
    });

    document.querySelectorAll('.quick-filter[data-tipo]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tipo === currentTipo);
    });
};

ExtratoApp.applyQuickFilter = function(filterType, value) {
    const url = new URL(window.location);

    if (value === 'all') {
        url.searchParams.delete(filterType);
    } else {
        url.searchParams.set(filterType, value);
    }

    // Reset para página 1
    url.searchParams.set('page', '1');

    window.location = url;
};

ExtratoApp.submitFilters = function() {
    const url = new URL(window.location);

    // Tipo
    if (this.elements.filterTipo && this.elements.filterTipo.value) {
        url.searchParams.set('tipo', this.elements.filterTipo.value);
    } else {
        url.searchParams.delete('tipo');
    }

    // Data De
    if (this.elements.filterDataDe && this.elements.filterDataDe.value) {
        url.searchParams.set('data_de', this.elements.filterDataDe.value);
    } else {
        url.searchParams.delete('data_de');
    }

    // Data Até
    if (this.elements.filterDataAte && this.elements.filterDataAte.value) {
        url.searchParams.set('data_ate', this.elements.filterDataAte.value);
    } else {
        url.searchParams.delete('data_ate');
    }

    // Status
    if (this.elements.filterStatus && this.elements.filterStatus.value) {
        url.searchParams.set('status', this.elements.filterStatus.value);
    } else {
        url.searchParams.delete('status');
    }

    // Journal
    if (this.elements.filterJournal && this.elements.filterJournal.value) {
        url.searchParams.set('journal', this.elements.filterJournal.value);
    } else {
        url.searchParams.delete('journal');
    }

    // Per page
    if (this.elements.perPageSelect && this.elements.perPageSelect.value) {
        url.searchParams.set('per_page', this.elements.perPageSelect.value);
    }

    // Reset para página 1
    url.searchParams.set('page', '1');

    window.location = url;
};

ExtratoApp.clearFilters = function() {
    const url = new URL(window.location);
    url.search = '';
    window.location = url;
};

// =============================================================================
// SELEÇÃO DE LOTES (IMPORTADOS)
// =============================================================================

ExtratoApp.toggleLote = function(checkbox, loteId) {
    if (checkbox.checked) {
        this.selectedLotes.add(loteId);
    } else {
        this.selectedLotes.delete(loteId);
    }

    // Atualizar estado visual da linha
    const row = checkbox.closest('tr');
    row.classList.toggle('selected', checkbox.checked);

    // Atualizar select all
    this.updateSelectAllState('lotes');

    // Atualizar bulk actions
    this.updateBulkActions();
};

// Toggle para lotes agrupados (recebimento + pagamento na mesma linha)
ExtratoApp.toggleLoteAgrupado = function(checkbox) {
    const loteRecId = checkbox.dataset.loteRec ? parseInt(checkbox.dataset.loteRec) : null;
    const lotePagId = checkbox.dataset.lotePag ? parseInt(checkbox.dataset.lotePag) : null;

    if (checkbox.checked) {
        if (loteRecId) this.selectedLotes.add(loteRecId);
        if (lotePagId) this.selectedLotes.add(lotePagId);
    } else {
        if (loteRecId) this.selectedLotes.delete(loteRecId);
        if (lotePagId) this.selectedLotes.delete(lotePagId);
    }

    // Atualizar estado visual da linha
    const row = checkbox.closest('tr');
    row.classList.toggle('selected', checkbox.checked);

    // Atualizar select all
    this.updateSelectAllState('lotes');

    // Atualizar bulk actions
    this.updateBulkActions();
};

// Função global para onclick inline
function toggleLoteAgrupado(checkbox) {
    ExtratoApp.toggleLoteAgrupado(checkbox);
}

ExtratoApp.toggleAllLotes = function(checked) {
    document.querySelectorAll('.lote-checkbox').forEach(cb => {
        cb.checked = checked;
        const loteId = parseInt(cb.value);
        const row = cb.closest('tr');

        if (checked) {
            this.selectedLotes.add(loteId);
            row.classList.add('selected');
        } else {
            this.selectedLotes.delete(loteId);
            row.classList.remove('selected');
        }
    });

    this.updateBulkActions();
};

ExtratoApp.updateSelectAllState = function(type) {
    if (type === 'lotes') {
        const checkboxes = document.querySelectorAll('.lote-checkbox');
        const checkedCount = document.querySelectorAll('.lote-checkbox:checked').length;

        if (this.elements.selectAllLotes) {
            this.elements.selectAllLotes.checked = checkedCount === checkboxes.length && checkboxes.length > 0;
            this.elements.selectAllLotes.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
        }
    }
};

// =============================================================================
// SELEÇÃO DE STATEMENTS (PENDENTES)
// =============================================================================

ExtratoApp.toggleStatement = function(checkbox, statementId) {
    if (checkbox.checked) {
        this.selectedStatements.add(statementId);
    } else {
        this.selectedStatements.delete(statementId);
    }

    const row = checkbox.closest('tr');
    row.classList.toggle('selected', checkbox.checked);

    this.updateSelectAllState('pendentes');
    this.updateBulkActions();
};

ExtratoApp.toggleAllPendentes = function(checked) {
    document.querySelectorAll('.statement-checkbox').forEach(cb => {
        cb.checked = checked;
        const statementId = parseInt(cb.value);
        const row = cb.closest('tr');

        if (checked) {
            this.selectedStatements.add(statementId);
            row.classList.add('selected');
        } else {
            this.selectedStatements.delete(statementId);
            row.classList.remove('selected');
        }
    });

    this.updateBulkActions();
};

// =============================================================================
// BULK ACTIONS
// =============================================================================

ExtratoApp.updateBulkActions = function() {
    const totalStatements = this.selectedStatements.size;
    const totalSelected = this.selectedLotes.size + totalStatements;

    if (this.elements.bulkActionsBar) {
        this.elements.bulkActionsBar.classList.toggle('visible', totalSelected > 0);

        if (this.elements.bulkCount) {
            this.elements.bulkCount.textContent = totalSelected;
        }

        if (this.elements.bulkText) {
            const partes = [];

            if (this.selectedLotes.size > 0) {
                partes.push(`${this.selectedLotes.size} lote(s)`);
            }
            if (totalStatements > 0) {
                // Mostrar detalhes de quantos tem rec/pag
                const temRec = this.selectedRecebimentos.size > 0;
                const temPag = this.selectedPagamentos.size > 0;
                let detalhe = `${totalStatements} pendente(s)`;
                if (temRec && temPag) {
                    detalhe += ' (rec+pag)';
                } else if (temRec) {
                    detalhe += ' (rec)';
                } else if (temPag) {
                    detalhe += ' (pag)';
                }
                partes.push(detalhe);
            }

            this.elements.bulkText.textContent = partes.join(' + ') || 'selecionado(s)';
        }
    }
};

ExtratoApp.clearSelection = function() {
    this.selectedLotes.clear();
    this.selectedStatements.clear();
    this.selectedRecebimentos.clear();
    this.selectedPagamentos.clear();

    document.querySelectorAll('.lote-checkbox, .statement-checkbox').forEach(cb => {
        cb.checked = false;
        cb.closest('tr')?.classList.remove('selected');
    });

    if (this.elements.selectAllLotes) this.elements.selectAllLotes.checked = false;
    if (this.elements.selectAllPendentes) this.elements.selectAllPendentes.checked = false;

    this.updateBulkActions();
};

ExtratoApp.verLotesSelecionados = function() {
    if (this.selectedLotes.size === 0) {
        this.showToast('Selecione ao menos um lote', 'warning');
        return;
    }

    const loteIds = Array.from(this.selectedLotes).join(',');
    window.location.href = `${this.config.apiBaseUrl}/lotes-detalhe?lotes=${loteIds}`;
};

// =============================================================================
// CARREGAMENTO DE STATEMENTS (AJAX) - UNIFICADO
// =============================================================================

ExtratoApp.loadStatements = function() {
    const tbody = this.elements.pendentesTable;
    if (!tbody) return;

    // Mostrar loading
    tbody.innerHTML = `
        <tr>
            <td colspan="6">
                <div class="extrato-loading">
                    <div class="extrato-loading__spinner"></div>
                    <div class="extrato-loading__text">Buscando extratos do Odoo...</div>
                </div>
            </td>
        </tr>
    `;

    // Buscar AMBOS os tipos de uma vez
    fetch(`${this.config.apiBaseUrl}/api/statements?tipo=ambos`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.statementsRecebimentos = data.statements_entrada || [];
                this.statementsPagamentos = data.statements_saida || [];
                this.renderPendentesUnificado();
                this.updateStatsFromStatements();
            } else {
                this.showPendentesError(data.error || 'Erro ao buscar dados');
            }
        })
        .catch(error => {
            this.showPendentesError(error.message);
        });
};

ExtratoApp.renderPendentesUnificado = function() {
    const tbody = this.elements.pendentesTable;
    if (!tbody) return;

    // Filtrar pendentes de cada tipo
    const recPendentes = this.statementsRecebimentos.filter(st => st.pendentes_odoo > 0 && !st.importado);
    const pagPendentes = this.statementsPagamentos.filter(st => st.pendentes_odoo > 0 && !st.importado);

    // Mesclar por statement_id (mesmo extrato pode ter rec + pag)
    const merged = new Map();

    recPendentes.forEach(st => {
        merged.set(st.statement_id, {
            ...st,
            rec: st,
            pag: null
        });
    });

    pagPendentes.forEach(st => {
        if (merged.has(st.statement_id)) {
            merged.get(st.statement_id).pag = st;
        } else {
            merged.set(st.statement_id, {
                ...st,
                rec: null,
                pag: st
            });
        }
    });

    const pendentes = Array.from(merged.values());
    const totalPendentes = pendentes.length;

    // Atualizar badge
    if (this.elements.badgePendentesTotal) {
        this.elements.badgePendentesTotal.textContent = totalPendentes;
    }

    if (totalPendentes === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="extrato-empty">
                        <div class="extrato-empty__icon"><i class="fas fa-check-circle" style="color: var(--fin-accent-success);"></i></div>
                        <div class="extrato-empty__title">Nenhum extrato pendente</div>
                        <div class="extrato-empty__text">Todos os extratos do Odoo foram importados</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    pendentes.forEach(item => {
        const st = item.rec || item.pag;
        const recLinhas = item.rec ? item.rec.pendentes_odoo : 0;
        const pagLinhas = item.pag ? item.pag.pendentes_odoo : 0;
        const totalLinhas = recLinhas + pagLinhas;

        html += `
            <tr data-statement-id="${st.statement_id}">
                <td>
                    <label class="fin-sr-only" for="stmt-${st.statement_id}">Selecionar extrato ${st.statement_id}</label>
                    <input type="checkbox" id="stmt-${st.statement_id}" class="extrato-checkbox statement-checkbox"
                           value="${st.statement_id}"
                           data-rec-pendentes="${recLinhas}"
                           data-pag-pendentes="${pagLinhas}"
                           onchange="ExtratoApp.toggleStatement(this, ${st.statement_id})">
                </td>
                <td>
                    <div class="fin-text-mono">${this.escapeHtml(st.name)}</div>
                    <small class="text-muted">
                        <span class="journal-badge">${this.escapeHtml(st.journal_code || 'N/A')}</span>
                        ID: ${st.statement_id}
                    </small>
                </td>
                <td class="fin-text-mono">${st.date || '-'}</td>
                <!-- RECEBIMENTO -->
                <td class="fin-td-macro fin-td-macro--rec fin-text-center">
                    ${recLinhas > 0 ? `<strong class="fin-stat-unified__label--rec">${recLinhas}</strong>` : `<span class="fin-na">-</span>`}
                </td>
                <!-- PAGAMENTO -->
                <td class="fin-td-macro fin-td-macro--pag fin-text-center">
                    ${pagLinhas > 0 ? `<strong class="fin-stat-unified__label--pag">${pagLinhas}</strong>` : `<span class="fin-na">-</span>`}
                </td>
                <!-- AÇÃO ÚNICA -->
                <td class="fin-text-center">
                    <button class="btn-ext btn-ext--primary btn-ext--sm"
                            onclick="ExtratoApp.importarStatementCompleto(${st.statement_id}, ${recLinhas}, ${pagLinhas})"
                            title="Importar extrato completo (${totalLinhas} linhas)">
                        <i class="fas fa-download"></i> Importar
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
};

ExtratoApp.showPendentesError = function(message) {
    const tbody = this.elements.pendentesTable;
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="6">
                <div class="extrato-empty">
                    <div class="extrato-empty__icon"><i class="fas fa-exclamation-triangle" style="color: var(--fin-accent-danger);"></i></div>
                    <div class="extrato-empty__title">Erro ao carregar extratos</div>
                    <div class="extrato-empty__text">${this.escapeHtml(message)}</div>
                    <button class="btn-ext btn-ext--ghost" onclick="ExtratoApp.loadStatements()" style="margin-top: 1rem;">
                        <i class="fas fa-redo"></i> Tentar novamente
                    </button>
                </div>
            </td>
        </tr>
    `;
};

ExtratoApp.updateStatsFromStatements = function() {
    // Recebimentos pendentes
    const recebimentosPendentes = this.statementsRecebimentos
        .filter(st => st.pendentes_odoo > 0 && !st.importado)
        .reduce((sum, st) => sum + (st.pendentes_odoo || 0), 0);
    const elRecebimentos = document.getElementById('statPendentesRecebimentos');
    if (elRecebimentos) {
        elRecebimentos.textContent = recebimentosPendentes;
    }

    // Pagamentos pendentes
    const pagamentosPendentes = this.statementsPagamentos
        .filter(st => st.pendentes_odoo > 0 && !st.importado)
        .reduce((sum, st) => sum + (st.pendentes_odoo || 0), 0);
    const elPagamentos = document.getElementById('statPendentesPagamentos');
    if (elPagamentos) {
        elPagamentos.textContent = pagamentosPendentes;
    }
};

// Toggle de seleção unificado para statements
ExtratoApp.toggleStatement = function(checkbox, statementId) {
    const recPendentes = parseInt(checkbox.dataset.recPendentes) || 0;
    const pagPendentes = parseInt(checkbox.dataset.pagPendentes) || 0;

    if (checkbox.checked) {
        this.selectedStatements.add(statementId);
        // Também adicionar nos sets específicos se houver pendentes
        if (recPendentes > 0) this.selectedRecebimentos.add(statementId);
        if (pagPendentes > 0) this.selectedPagamentos.add(statementId);
    } else {
        this.selectedStatements.delete(statementId);
        this.selectedRecebimentos.delete(statementId);
        this.selectedPagamentos.delete(statementId);
    }

    const row = checkbox.closest('tr');
    row.classList.toggle('selected', checkbox.checked);

    this.updateBulkActions();
};

ExtratoApp.toggleAllPendentes = function(checked) {
    document.querySelectorAll('.statement-checkbox').forEach(cb => {
        cb.checked = checked;
        const statementId = parseInt(cb.value);
        const recPendentes = parseInt(cb.dataset.recPendentes) || 0;
        const pagPendentes = parseInt(cb.dataset.pagPendentes) || 0;
        const row = cb.closest('tr');

        if (checked) {
            this.selectedStatements.add(statementId);
            if (recPendentes > 0) this.selectedRecebimentos.add(statementId);
            if (pagPendentes > 0) this.selectedPagamentos.add(statementId);
            row.classList.add('selected');
        } else {
            this.selectedStatements.delete(statementId);
            this.selectedRecebimentos.delete(statementId);
            this.selectedPagamentos.delete(statementId);
            row.classList.remove('selected');
        }
    });

    this.updateBulkActions();
};

// =============================================================================
// IMPORTAÇÃO
// =============================================================================

ExtratoApp.importarStatement = function(statementId, tipo = 'entrada') {
    const tipoLabel = tipo === 'entrada' ? 'recebimentos' : 'pagamentos';
    if (!confirm(`Importar ${tipoLabel} deste extrato?`)) return;

    // Criar form e submeter
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `${this.config.apiBaseUrl}/importar-statement/${statementId}?tipo=${tipo}`;

    // Adicionar campo hidden para o tipo
    const tipoInput = document.createElement('input');
    tipoInput.type = 'hidden';
    tipoInput.name = 'tipo';
    tipoInput.value = tipo;
    form.appendChild(tipoInput);

    document.body.appendChild(form);
    form.submit();
};

// Importar extrato completo (recebimentos + pagamentos)
ExtratoApp.importarStatementCompleto = function(statementId, recLinhas, pagLinhas) {
    const totalLinhas = recLinhas + pagLinhas;
    let detalhes = [];
    if (recLinhas > 0) detalhes.push(`${recLinhas} receb.`);
    if (pagLinhas > 0) detalhes.push(`${pagLinhas} pagam.`);

    if (!confirm(`Importar extrato completo?\n\n${detalhes.join(' + ')} = ${totalLinhas} linha(s)`)) return;

    this.showToast('Importando extrato...', 'info');

    // Importar ambos os tipos em paralelo
    const promessas = [];

    if (recLinhas > 0) {
        promessas.push(
            fetch(`${this.config.apiBaseUrl}/importar-multiplos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    statement_ids: [statementId],
                    tipo: 'entrada'
                })
            }).then(r => r.json())
        );
    }

    if (pagLinhas > 0) {
        promessas.push(
            fetch(`${this.config.apiBaseUrl}/importar-multiplos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    statement_ids: [statementId],
                    tipo: 'saida'
                })
            }).then(r => r.json())
        );
    }

    Promise.all(promessas)
        .then(resultados => {
            const linhasImportadas = resultados.reduce((sum, r) => sum + (r.total_linhas || 0), 0);
            const erros = resultados.filter(r => !r.success);

            if (erros.length === 0) {
                this.showToast(`Extrato importado: ${linhasImportadas} linhas`, 'success');
            } else {
                this.showToast('Importado com alguns erros', 'warning');
            }

            setTimeout(() => window.location.reload(), 1500);
        })
        .catch(error => {
            this.showToast('Erro: ' + error.message, 'error');
        });
};

ExtratoApp.importarSelecionados = function() {
    const totalStatements = this.selectedStatements.size;
    const temRecebimentos = this.selectedRecebimentos.size > 0;
    const temPagamentos = this.selectedPagamentos.size > 0;

    if (totalStatements === 0) {
        this.showToast('Selecione ao menos um extrato pendente', 'warning');
        return;
    }

    let msg = `Importar ${totalStatements} extrato(s)`;
    if (temRecebimentos && temPagamentos) {
        msg += ' (recebimentos + pagamentos)';
    } else if (temRecebimentos) {
        msg += ' (recebimentos)';
    } else {
        msg += ' (pagamentos)';
    }
    msg += '?';

    if (!confirm(msg)) return;

    // Mostrar loading
    this.showToast('Importando extratos...', 'info');

    // Importar por tipo
    const promessas = [];

    if (temRecebimentos) {
        promessas.push(
            fetch(`${this.config.apiBaseUrl}/importar-multiplos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    statement_ids: Array.from(this.selectedRecebimentos),
                    tipo: 'entrada'
                })
            }).then(r => r.json())
        );
    }

    if (temPagamentos) {
        promessas.push(
            fetch(`${this.config.apiBaseUrl}/importar-multiplos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    statement_ids: Array.from(this.selectedPagamentos),
                    tipo: 'saida'
                })
            }).then(r => r.json())
        );
    }

    Promise.all(promessas)
        .then(resultados => {
            const importados = resultados.reduce((sum, r) => sum + (r.importados || 0), 0);
            const linhas = resultados.reduce((sum, r) => sum + (r.total_linhas || 0), 0);
            const erros = resultados.filter(r => !r.success).length;

            if (erros === 0) {
                this.showToast(`${importados} extrato(s) importado(s) com ${linhas} linhas`, 'success');
            } else {
                this.showToast(`Importado(s) ${importados} com alguns erros`, 'warning');
            }

            setTimeout(() => window.location.reload(), 1500);
        })
        .catch(error => {
            this.showToast('Erro na requisição: ' + error.message, 'error');
        });
};

// =============================================================================
// CONCILIAÇÃO
// =============================================================================

ExtratoApp.conciliarRecebimentos = function() {
    // Filtrar apenas lotes de recebimento selecionados
    const lotesRec = Array.from(this.selectedLotes).filter(loteId => {
        const row = document.querySelector(`tr[data-lote-id="${loteId}"]`);
        return row && row.querySelector('.td-macro--rec:not(:has(.na-text))');
    });

    if (lotesRec.length === 0) {
        this.showToast('Selecione ao menos um lote de recebimento', 'warning');
        return;
    }

    // Redirecionar para a tela de conciliação em lote (recebimentos)
    const loteIds = lotesRec.join(',');
    window.location.href = `${this.config.apiBaseUrl}/lotes-detalhe?lotes=${loteIds}&tipo=entrada`;
};

ExtratoApp.conciliarPagamentos = function() {
    // Filtrar apenas lotes de pagamento selecionados
    const lotesPag = Array.from(this.selectedLotes).filter(loteId => {
        const row = document.querySelector(`tr[data-lote-id="${loteId}"]`);
        return row && row.querySelector('.td-macro--pag:not(:has(.na-text))');
    });

    if (lotesPag.length === 0) {
        this.showToast('Selecione ao menos um lote de pagamento', 'warning');
        return;
    }

    // Redirecionar para a tela de conciliação em lote (pagamentos)
    const loteIds = lotesPag.join(',');
    window.location.href = `${this.config.apiBaseUrl}/lotes-detalhe?lotes=${loteIds}&tipo=saida`;
};

// =============================================================================
// UTILITÁRIOS
// =============================================================================

ExtratoApp.escapeHtml = function(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

ExtratoApp.showToast = function(message, type = 'info') {
    // Se toastr está disponível, usar
    if (typeof toastr !== 'undefined') {
        toastr[type](message);
        return;
    }

    // Fallback simples
    alert(message);
};

ExtratoApp.formatDate = function(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR');
};

ExtratoApp.formatCurrency = function(value) {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
};

// =============================================================================
// FUNÇÕES GLOBAIS (para onclick inline)
// =============================================================================

function toggleLote(checkbox, loteId) {
    ExtratoApp.toggleLote(checkbox, loteId);
}

function verLotesSelecionados() {
    ExtratoApp.verLotesSelecionados();
}

function importarSelecionados() {
    ExtratoApp.importarSelecionados();
}

function clearSelection() {
    ExtratoApp.clearSelection();
}

function clearFilters() {
    ExtratoApp.clearFilters();
}
