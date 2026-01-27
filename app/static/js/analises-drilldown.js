/**
 * ============================================
 * ANALISES DE FRETES - DRILL-DOWN DINAMICO
 * ============================================
 *
 * Sistema de análise drill-down interativo que permite
 * navegação progressiva em até 6 níveis de profundidade
 * com breadcrumb navegável e exportação para Excel.
 *
 * Autor: Sistema Logística Nacom Goya
 * Data: 2025-01-16
 */

// ========== DESIGN TOKENS FOR CHART COLORS ==========
const ChartDesignTokens = {
    get(name) {
        return getComputedStyle(document.documentElement)
            .getPropertyValue(`--${name}`).trim();
    },
    // Chart colors - use design system tokens
    primary: () => ChartDesignTokens.get('chart-primary') || ChartDesignTokens.get('bs-primary') || 'hsl(210 65% 55%)',
    secondary: () => ChartDesignTokens.get('chart-secondary') || ChartDesignTokens.get('semantic-danger') || 'hsl(0 70% 55%)'
};

// ========== CONFIGURACAO GLOBAL ==========
const CONFIG = {
    API_URL: '/fretes/analises/api/data',
    EXPORT_URL: '/fretes/analises/api/export-excel',
    MAX_DRILL_DEPTH: 6,
    DIMENSIONS: {
        uf: { label: 'UF', icon: 'fa-map-marked-alt' },
        transportadora: { label: 'Transportadora', icon: 'fa-truck' },
        modalidade: { label: 'Veículo', icon: 'fa-truck-moving' },
        mes: { label: 'Mês', icon: 'fa-calendar' },
        subrota: { label: 'Sub-rota', icon: 'fa-route' },
        cliente: { label: 'Cliente', icon: 'fa-building' }
    }
};

// ========== CLASSE DE GERENCIAMENTO DE ESTADO ==========
class AppState {
    constructor() {
        this.drillPath = [];  // [{type: 'uf', value: 'SP', label: 'SP'}]
        this.currentData = [];
        this.currentDimension = null;
        this.incluirTransportadora = true;  // Checkbox Transportadora
        this.incluirFreteiro = true;  // Checkbox Freteiro
        this.loadFromURL();
    }

    /**
     * Adiciona um novo filtro ao drill path
     */
    addFilter(type, value, label) {
        this.drillPath.push({ type, value, label });
        this.saveToURL();
    }

    /**
     * Remove um filtro específico do drill path
     * OPÇÃO B: Mantém os filtros subsequentes
     */
    removeFilter(index) {
        this.drillPath.splice(index, 1);
        this.saveToURL();
    }

    /**
     * Reseta todo o estado
     */
    reset() {
        this.drillPath = [];
        this.currentData = [];
        this.currentDimension = null;
        this.saveToURL();
    }

    /**
     * Salva o estado atual na URL
     */
    saveToURL() {
        const params = new URLSearchParams();
        if (this.drillPath.length > 0) {
            params.set('drill', JSON.stringify(this.drillPath));
        }
        if (this.currentDimension) {
            params.set('dimension', this.currentDimension);
        }
        // Salvar estado dos checkboxes
        params.set('transportadora', this.incluirTransportadora);
        params.set('freteiro', this.incluirFreteiro);

        const newURL = `${window.location.pathname}?${params.toString()}`;
        window.history.pushState({}, '', newURL);
    }

    /**
     * Carrega o estado da URL
     */
    loadFromURL() {
        const params = new URLSearchParams(window.location.search);
        const drillParam = params.get('drill');
        const dimensionParam = params.get('dimension');
        const transportadoraParam = params.get('transportadora');
        const freteiroParam = params.get('freteiro');

        if (drillParam) {
            try {
                this.drillPath = JSON.parse(drillParam);
            } catch (e) {
                console.error('Erro ao parsear drill path da URL:', e);
                this.drillPath = [];
            }
        }

        if (dimensionParam) {
            this.currentDimension = dimensionParam;
        }

        // Carregar estado dos checkboxes da URL
        if (transportadoraParam !== null) {
            this.incluirTransportadora = transportadoraParam === 'true';
        }
        if (freteiroParam !== null) {
            this.incluirFreteiro = freteiroParam === 'true';
        }
    }

    /**
     * Retorna as dimensões já usadas no drill path
     */
    getUsedDimensions() {
        return this.drillPath.map(f => f.type);
    }

    /**
     * Retorna as dimensões disponíveis para próximo drill
     */
    getAvailableDimensions() {
        const used = this.getUsedDimensions();
        return Object.keys(CONFIG.DIMENSIONS).filter(d => !used.includes(d));
    }

    /**
     * Verifica se pode adicionar mais filtros
     */
    canAddFilter() {
        return this.drillPath.length < CONFIG.MAX_DRILL_DEPTH;
    }
}

// Instância global do estado
const state = new AppState();

// ========== INICIALIZAÇÃO ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Iniciando Análises Drill-Down...');

    // Carregar Google Charts
    google.charts.load('current', { packages: ['corechart', 'bar'] });
    google.charts.setOnLoadCallback(init);
});

function init() {
    console.log('📊 Google Charts carregado');
    setupEventListeners();
    syncCheckboxes();  // Sincronizar checkboxes com estado

    // Se tem drill path na URL, carregar dados automaticamente
    if (state.drillPath.length > 0 && state.currentDimension) {
        console.log('🔄 Restaurando estado da URL:', state.drillPath);
        loadData(state.currentDimension);
    }

    renderBreadcrumb();
}

/**
 * Sincroniza os checkboxes com o estado atual
 */
function syncCheckboxes() {
    document.getElementById('check-transportadora').checked = state.incluirTransportadora;
    document.getElementById('check-freteiro').checked = state.incluirFreteiro;
}

// ========== EVENT LISTENERS ==========
function setupEventListeners() {
    // Botões de dimensão inicial
    document.querySelectorAll('.dimension-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const dimension = this.dataset.dimension;
            console.log('📌 Dimensão selecionada:', dimension);
            loadData(dimension);
        });
    });

    // Botão reset
    document.getElementById('btn-reset').addEventListener('click', function() {
        console.log('🏠 Reset - voltando ao início');
        state.reset();
        hideDimensionSelector(false);
        hideDataContainer();
        hideMetrics();
        renderBreadcrumb();
    });

    // Botão de exportação Excel
    document.getElementById('btn-export-excel').addEventListener('click', function() {
        console.log('📥 Exportando para Excel...');
        exportToExcel();
    });

    // Checkboxes de Transportadora e Freteiro
    document.getElementById('check-transportadora').addEventListener('change', function() {
        state.incluirTransportadora = this.checked;
        console.log('📦 Checkbox Transportadora:', state.incluirTransportadora);
        // Recarregar dados se já houver dimensão selecionada
        if (state.currentDimension) {
            loadData(state.currentDimension);
        }
    });

    document.getElementById('check-freteiro').addEventListener('change', function() {
        state.incluirFreteiro = this.checked;
        console.log('👤 Checkbox Freteiro:', state.incluirFreteiro);
        // Recarregar dados se já houver dimensão selecionada
        if (state.currentDimension) {
            loadData(state.currentDimension);
        }
    });

    // Fechar menu contextual ao clicar fora
    document.addEventListener('click', function(e) {
        if (!e.target.closest('#drill-menu') && !e.target.closest('[data-drillable]')) {
            hideDrillMenu();
        }
    });

    // Navegação do browser (back/forward)
    window.addEventListener('popstate', function() {
        console.log('⬅️ Navegação do browser detectada');
        state.loadFromURL();
        if (state.currentDimension) {
            loadData(state.currentDimension);
        } else {
            state.reset();
            hideDimensionSelector(false);
            hideDataContainer();
            hideMetrics();
        }
        renderBreadcrumb();
    });
}

// ========== CHAMADAS À API ==========

/**
 * Carrega dados da API baseado na dimensão de agrupamento
 */
async function loadData(groupBy) {
    console.log('📡 Carregando dados - GroupBy:', groupBy, 'Filtros:', state.drillPath);
    console.log('📦 Transportadora:', state.incluirTransportadora, 'Freteiro:', state.incluirFreteiro);

    showLoading();

    try {
        const filters = state.drillPath.map(f => ({ type: f.type, value: f.value }));
        const params = new URLSearchParams({
            filters: JSON.stringify(filters),
            group_by: groupBy,
            incluir_transportadora: state.incluirTransportadora,
            incluir_freteiro: state.incluirFreteiro
        });

        const response = await fetch(`${CONFIG.API_URL}?${params.toString()}`);
        const result = await response.json();

        if (result.success) {
            state.currentData = result.dados;
            state.currentDimension = groupBy;

            console.log('✅ Dados carregados:', result.dados.length, 'registros');

            hideDimensionSelector(true);
            showDataContainer();
            showMetrics();

            renderBreadcrumb();
            renderChart();
            renderTable();
            calculateMetrics();
        } else {
            console.error('❌ Erro na resposta da API:', result.error);
            alert('Erro ao carregar dados: ' + (result.error || 'Erro desconhecido'));
        }
    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        alert('Erro ao carregar dados. Verifique o console para mais detalhes.');
    } finally {
        hideLoading();
    }
}

/**
 * Exporta dados atuais para Excel
 */
function exportToExcel() {
    const filters = state.drillPath.map(f => ({ type: f.type, value: f.value }));
    const params = new URLSearchParams({
        filters: JSON.stringify(filters),
        group_by: state.currentDimension,
        incluir_transportadora: state.incluirTransportadora,
        incluir_freteiro: state.incluirFreteiro
    });

    const url = `${CONFIG.EXPORT_URL}?${params.toString()}`;
    console.log('📥 URL de exportação:', url);

    // Abrir em nova janela para download
    window.location.href = url;
}

// ========== RENDERIZAÇÃO: BREADCRUMB ==========

/**
 * Renderiza o breadcrumb com os filtros aplicados
 */
function renderBreadcrumb() {
    const container = document.getElementById('drill-breadcrumb');

    // Limpar breadcrumb items anteriores (manter botão início)
    const items = container.querySelectorAll('.breadcrumb-item');
    items.forEach(item => item.remove());

    // Adicionar filtros aplicados
    state.drillPath.forEach((filter, index) => {
        const item = document.createElement('div');
        item.className = 'breadcrumb-item';

        // Truncar label se for muito longo
        let displayLabel = filter.label;
        if (displayLabel.length > 30) {
            displayLabel = displayLabel.substring(0, 27) + '...';
        }

        item.innerHTML = `
            <i class="fas ${CONFIG.DIMENSIONS[filter.type].icon}"></i>
            <span title="${filter.label}">${displayLabel}</span>
            <button class="btn-remove" data-index="${index}" title="Remover este filtro">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Event listener para remover
        item.querySelector('.btn-remove').addEventListener('click', function() {
            const idx = parseInt(this.dataset.index);
            console.log('❌ Removendo filtro:', state.drillPath[idx]);

            state.removeFilter(idx);

            // Recarregar dados com os filtros restantes
            if (state.drillPath.length > 0 || state.currentDimension) {
                // Manter a dimensão atual se ainda tiver dados
                loadData(state.currentDimension);
            } else {
                // Sem filtros e sem dimensão, voltar ao início
                hideDimensionSelector(false);
                hideDataContainer();
                hideMetrics();
            }

            renderBreadcrumb();
        });

        container.appendChild(item);
    });

    // Adicionar indicador da dimensão atual (se houver dados)
    if (state.currentDimension && state.currentData.length > 0) {
        const current = document.createElement('div');
        current.className = 'breadcrumb-item breadcrumb-current';
        current.innerHTML = `
            <i class="fas ${CONFIG.DIMENSIONS[state.currentDimension].icon}"></i>
            <span>Agrupado por ${CONFIG.DIMENSIONS[state.currentDimension].label}</span>
        `;
        container.appendChild(current);
    }
}

// ========== RENDERIZAÇÃO: GRÁFICO ==========

/**
 * Renderiza o gráfico com Google Charts
 */
function renderChart() {
    const container = document.getElementById('drill-chart');

    if (!state.currentData || state.currentData.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-chart-bar"></i>
                <h5>Nenhum dado disponível</h5>
                <p>Não há dados para exibir com os filtros aplicados.</p>
            </div>
        `;
        return;
    }

    // Preparar dados para Google Charts
    const dataTable = new google.visualization.DataTable();
    dataTable.addColumn('string', CONFIG.DIMENSIONS[state.currentDimension].label);
    dataTable.addColumn('number', '% s/ Valor NF');
    dataTable.addColumn({type: 'string', role: 'tooltip', p: {html: true}});
    dataTable.addColumn('number', 'R$/KG');
    dataTable.addColumn({type: 'string', role: 'tooltip', p: {html: true}});

    state.currentData.forEach(item => {
        const tooltipPerc = createTooltip(item, '% s/ Valor NF', item.percentual_valor);
        const tooltipRsKg = createTooltip(item, 'R$/KG', item.valor_por_kg);

        // Truncar labels longos
        let displayLabel = item.label;
        if (displayLabel.length > 20) {
            displayLabel = displayLabel.substring(0, 17) + '...';
        }

        dataTable.addRow([
            displayLabel,
            item.percentual_valor,
            tooltipPerc,
            item.valor_por_kg,
            tooltipRsKg
        ]);
    });

    const options = {
        title: `Análise por ${CONFIG.DIMENSIONS[state.currentDimension].label}`,
        width: '100%',
        height: 500,
        series: {
            0: {targetAxisIndex: 0, color: ChartDesignTokens.primary()},
            1: {targetAxisIndex: 1, color: ChartDesignTokens.secondary()}
        },
        vAxes: {
            0: {
                title: '% sobre Valor NF',
                viewWindow: {min: 0}  // Sempre começar do zero
            },
            1: {
                title: 'R$/KG',
                viewWindow: {min: 0}  // Sempre começar do zero
            }
        },
        hAxis: {
            title: CONFIG.DIMENSIONS[state.currentDimension].label,
            slantedText: true,
            slantedTextAngle: 45
        },
        tooltip: {isHtml: true},
        legend: {position: 'top'},
        chartArea: {width: '85%', height: '70%'}
    };

    const chart = new google.visualization.ColumnChart(container);

    // Event listener para clique nas barras
    google.visualization.events.addListener(chart, 'select', function() {
        const selection = chart.getSelection();
        if (selection.length > 0) {
            const rowIndex = selection[0].row;
            if (rowIndex !== null && rowIndex !== undefined) {
                const item = state.currentData[rowIndex];
                // Simular evento de clique para abrir menu
                const fakeEvent = { pageX: window.innerWidth / 2, pageY: window.innerHeight / 2 };
                showDrillMenu(item, fakeEvent);
            }
        }
    });

    chart.draw(dataTable, options);
}

/**
 * Cria tooltip HTML para o gráfico
 */
function createTooltip(item, metricName, metricValue) {
    return `
        <div style="padding: 12px; min-width: 200px;">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 14px;">${item.label}</div>
            <div style="margin-bottom: 4px;"><b>${metricName}:</b> ${metricValue.toFixed(2)}${metricName.includes('%') ? '%' : ''}</div>
            <div style="margin-bottom: 4px;"><b>Fretes:</b> ${item.qtd_fretes}</div>
            <div style="margin-bottom: 4px;"><b>Custo Total:</b> R$ ${formatNumber(item.total_custo)}</div>
            <div style="margin-bottom: 4px;"><b>Valor NF:</b> R$ ${formatNumber(item.valor_nf)}</div>
            <div><b>Peso:</b> ${formatNumber(item.peso)} KG</div>
        </div>
    `;
}

// ========== RENDERIZAÇÃO: TABELA ==========

/**
 * Renderiza a tabela de dados
 */
function renderTable() {
    const thead = document.getElementById('table-header');
    const tbody = document.getElementById('table-body');

    // Header
    thead.innerHTML = `
        <tr>
            <th>${CONFIG.DIMENSIONS[state.currentDimension].label}</th>
            <th class="text-end">Qtd Fretes</th>
            <th class="text-end">Frete Líquido (R$)</th>
            <th class="text-end">Despesas (R$)</th>
            <th class="text-end">Custo Total (R$)</th>
            <th class="text-end">Valor NF (R$)</th>
            <th class="text-end">Peso (KG)</th>
            <th class="text-end">% s/ Valor</th>
            <th class="text-end">R$/KG</th>
        </tr>
    `;

    // Body
    tbody.innerHTML = '';

    if (!state.currentData || state.currentData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-5">
                    <div class="empty-state">
                        <i class="fas fa-table"></i>
                        <h5>Nenhum dado disponível</h5>
                        <p>Não há dados para exibir com os filtros aplicados.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    state.currentData.forEach(item => {
        const row = document.createElement('tr');
        row.className = 'table-row-drillable';
        row.dataset.drillable = 'true';
        row.dataset.item = JSON.stringify(item);

        // Truncar label se for muito longo
        let displayLabel = item.label;
        if (displayLabel.length > 50) {
            displayLabel = displayLabel.substring(0, 47) + '...';
        }

        row.innerHTML = `
            <td title="${item.label}"><strong>${displayLabel}</strong></td>
            <td class="text-end">${item.qtd_fretes}</td>
            <td class="text-end">${formatMoney(item.valor_frete)}</td>
            <td class="text-end">${formatMoney(item.valor_despesa)}</td>
            <td class="text-end"><strong>${formatMoney(item.total_custo)}</strong></td>
            <td class="text-end">${formatMoney(item.valor_nf)}</td>
            <td class="text-end">${formatNumber(item.peso)}</td>
            <td class="text-end">
                <span class="badge badge-percentual ${getBadgeClass(item.percentual_valor)}">
                    ${item.percentual_valor.toFixed(2)}%
                </span>
            </td>
            <td class="text-end"><strong>R$ ${item.valor_por_kg.toFixed(2)}</strong></td>
        `;

        // Event listener para drill-down
        row.addEventListener('click', function(e) {
            const itemData = JSON.parse(this.dataset.item);
            showDrillMenu(itemData, e);
        });

        tbody.appendChild(row);
    });
}

// ========== MENU CONTEXTUAL DE DRILL-DOWN ==========

/**
 * Mostra o menu contextual para seleção da próxima dimensão
 */
function showDrillMenu(item, event) {
    const available = state.getAvailableDimensions();

    if (available.length === 0) {
        alert(`Profundidade máxima atingida (${CONFIG.MAX_DRILL_DEPTH} níveis)`);
        return;
    }

    const menu = document.getElementById('drill-menu');
    const menuItems = menu.querySelector('.menu-items');

    // Limpar items
    menuItems.innerHTML = '';

    // Adicionar opções disponíveis
    available.forEach(dimension => {
        const option = document.createElement('button');
        option.className = 'menu-item';
        option.innerHTML = `
            <i class="fas ${CONFIG.DIMENSIONS[dimension].icon}"></i>
            ${CONFIG.DIMENSIONS[dimension].label}
        `;
        option.addEventListener('click', function() {
            console.log('🔽 Drill-down:', item.label, '→', dimension);

            // Adicionar filtro
            state.addFilter(state.currentDimension, item.label, item.label);

            // Carregar dados na nova dimensão
            loadData(dimension);

            // Fechar menu
            hideDrillMenu();
        });
        menuItems.appendChild(option);
    });

    // Posicionar menu próximo ao clique
    menu.style.display = 'block';
    menu.style.left = `${event.pageX + 10}px`;
    menu.style.top = `${event.pageY + 10}px`;

    // Ajustar posição se estiver fora da tela
    setTimeout(() => {
        const rect = menu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            menu.style.left = `${event.pageX - rect.width - 10}px`;
        }
        if (rect.bottom > window.innerHeight) {
            menu.style.top = `${event.pageY - rect.height - 10}px`;
        }
    }, 10);
}

/**
 * Esconde o menu contextual
 */
function hideDrillMenu() {
    document.getElementById('drill-menu').style.display = 'none';
}

// ========== CÁLCULO DE MÉTRICAS ==========

/**
 * Calcula e exibe as métricas totais dos dados atuais
 */
function calculateMetrics() {
    if (!state.currentData || state.currentData.length === 0) return;

    const totals = state.currentData.reduce((acc, item) => {
        acc.valor_nf += item.valor_nf;
        acc.peso += item.peso;
        acc.frete += item.valor_frete;
        acc.despesa += item.valor_despesa;
        return acc;
    }, { valor_nf: 0, peso: 0, frete: 0, despesa: 0 });

    const custo_total = totals.frete + totals.despesa;
    const percentual = totals.valor_nf > 0 ? (custo_total / totals.valor_nf * 100) : 0;
    const rskg = totals.peso > 0 ? (custo_total / totals.peso) : 0;

    document.getElementById('metric-valor').textContent = formatMoney(totals.valor_nf);
    document.getElementById('metric-peso').textContent = `${formatNumber(totals.peso)} KG`;
    document.getElementById('metric-frete').textContent = formatMoney(totals.frete);
    document.getElementById('metric-despesa').textContent = formatMoney(totals.despesa);
    document.getElementById('metric-percentual').textContent = `${percentual.toFixed(2)}%`;
    document.getElementById('metric-rskg').textContent = `R$ ${rskg.toFixed(2)}`;
}

// ========== HELPERS DE UI ==========

function hideDimensionSelector(hide) {
    document.getElementById('dimension-selector').style.display = hide ? 'none' : 'block';
}

function showDataContainer() {
    document.getElementById('data-container').style.display = 'block';
}

function hideDataContainer() {
    document.getElementById('data-container').style.display = 'none';
}

function showMetrics() {
    document.getElementById('metrics-cards').style.display = 'flex';
}

function hideMetrics() {
    document.getElementById('metrics-cards').style.display = 'none';
}

function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// ========== HELPERS DE FORMATAÇÃO ==========

function formatMoney(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatNumber(value) {
    return new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function getBadgeClass(percentual) {
    if (percentual < 5) return 'bg-success';
    if (percentual < 10) return 'bg-warning text-dark';
    return 'bg-danger';
}

// ========== LOG INICIAL ==========
console.log('📦 Módulo Análises Drill-Down carregado');
console.log('⚙️ Configuração:', CONFIG);
