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
    this.initFilters();
};

ExtratoApp.cacheElements = function() {
    this.elements = {
        // Seções
        lotesSection: document.getElementById('lotesSection'),

        // Tabelas
        lotesTable: document.getElementById('lotesTableBody'),

        // Checkboxes
        selectAllLotes: document.getElementById('selectAllLotes'),

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
// BULK ACTIONS
// =============================================================================

ExtratoApp.updateBulkActions = function() {
    const totalSelected = this.selectedLotes.size;

    if (this.elements.bulkActionsBar) {
        this.elements.bulkActionsBar.classList.toggle('visible', totalSelected > 0);

        if (this.elements.bulkCount) {
            this.elements.bulkCount.textContent = totalSelected;
        }

        if (this.elements.bulkText) {
            this.elements.bulkText.textContent = `${totalSelected} lote(s) selecionado(s)`;
        }
    }
};

ExtratoApp.clearSelection = function() {
    this.selectedLotes.clear();

    document.querySelectorAll('.lote-checkbox').forEach(cb => {
        cb.checked = false;
        cb.closest('tr')?.classList.remove('selected');
    });

    if (this.elements.selectAllLotes) this.elements.selectAllLotes.checked = false;

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

function clearSelection() {
    ExtratoApp.clearSelection();
}

function clearFilters() {
    ExtratoApp.clearFilters();
}
