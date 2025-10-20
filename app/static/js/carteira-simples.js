/**
 * Carteira Simplificada - JavaScript
 * Controla toda a lógica de edição inline, cálculos dinâmicos e ações
 */

(function() {
    'use strict';

    console.log('🚀 [Carteira Simples] JavaScript carregado e iniciado!');

    // ==============================================
    // ESTADO GLOBAL
    // ==============================================
    const state = {
        dados: [],
        filtrosAplicados: {},
        paginaAtual: 1,
        itensPorPagina: 10000, // ✅ SEM PAGINAÇÃO - carregar todos os itens filtrados
        totalItens: 0,
        estoqueProjetadoCache: {}, // Cache {cod_produto_data: {estoque_atual, projecoes}}
        projecaoEstoqueOffset: 0, // 🆕 OFFSET GLOBAL para paginação D0-D28 (não mais por linha)
        carregando: false, // Flag para evitar múltiplas chamadas simultâneas
        modalLoading: null, // Instância única do modal de loading

        // 🚀 VIRTUAL SCROLLING
        virtualScroll: {
            firstVisibleIndex: 0,
            lastVisibleIndex: 150,  // Renderizar primeiras 150 linhas
            rowHeight: 25,          // Altura estimada de cada linha
            bufferSize: 50          // Buffer de linhas extras (25 antes + 25 depois)
        }
    };

    // ==============================================
    // INICIALIZAÇÃO
    // ==============================================
    document.addEventListener('DOMContentLoaded', function() {
        inicializarEventos();
        restaurarFiltrosSalvos(); // 🚀 OTIMIZAÇÃO: Restaurar filtros do localStorage
        carregarDados();
    });

    function inicializarEventos() {
        // 🚨 EMERGÊNCIA: Limpar localStorage no carregamento se tiver problema
        try {
            const filtrosSalvos = localStorage.getItem('carteira_simples_filtros');
            if (filtrosSalvos) {
                const filtros = JSON.parse(filtrosSalvos);
                const todosVazios = Object.values(filtros).every(v => !v || v.trim() === '');
                if (todosVazios) {
                    console.warn('⚠️ localStorage com filtros inválidos detectado! Limpando...');
                    localStorage.removeItem('carteira_simples_filtros');
                }
            }
        } catch (e) {
            console.error('Erro ao validar localStorage:', e);
            localStorage.removeItem('carteira_simples_filtros');
        }

        // Filtros
        document.getElementById('btn-aplicar-filtros').addEventListener('click', aplicarFiltros);
        document.getElementById('btn-limpar-filtros').addEventListener('click', limparFiltros);

        // Enter nos inputs de filtro
        ['filtro-busca', 'filtro-municipio', 'filtro-data-pedido-de', 'filtro-data-pedido-ate',
         'filtro-data-entrega-de', 'filtro-data-entrega-ate'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') aplicarFiltros();
                });
            }
        });

        // Event delegation para ações na tabela
        document.getElementById('tbody-carteira').addEventListener('click', handleTableClick);
        document.getElementById('tbody-carteira').addEventListener('change', handleTableChange);
        document.getElementById('tbody-carteira').addEventListener('input', handleTableInput);
    }

    // ==============================================
    // CARREGAMENTO DE DADOS
    // ==============================================
    async function carregarDados() {
        // Evitar múltiplas chamadas simultâneas
        if (state.carregando) {
            console.log('⚠️ Já está carregando dados, aguardando...');
            return;
        }

        try {
            state.carregando = true;
            mostrarLoading(true);

            // Montar query params
            const params = new URLSearchParams({
                limit: state.itensPorPagina,
                offset: (state.paginaAtual - 1) * state.itensPorPagina,
                ...state.filtrosAplicados
            });

            const response = await fetch(`/carteira/simples/api/dados?${params}`);
            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao carregar dados');
            }

            state.dados = resultado.dados;
            state.totalItens = resultado.total;

            renderizarTabela();
            popularFiltrosRotas(); // 🆕 Popular filtros de rota/sub-rota
            atualizarIndicadorFiltros(); // 🆕 Mostrar indicador de filtros ativos

            // ✅ IMPORTANTE: Fechar loading DEPOIS de renderizar (assíncrono)
            setTimeout(() => {
                state.carregando = false;
                mostrarLoading(false);
            }, 100);

        } catch (erro) {
            console.error('Erro ao carregar dados:', erro);
            mostrarMensagem('Erro', `Erro ao carregar dados: ${erro.message}`, 'danger');
            state.carregando = false;
            mostrarLoading(false);
        }
    }

    function aplicarFiltros() {
        try {
            // ✅ Coletar APENAS filtros com valores não vazios
            const filtrosTemp = {
                busca_geral: document.getElementById('filtro-busca')?.value.trim() || '',  // 🆕 Busca em múltiplos campos
                estado: document.getElementById('filtro-estado')?.value.trim() || '',
                municipio: document.getElementById('filtro-municipio')?.value.trim() || '',
                rota: document.getElementById('filtro-rota')?.value.trim() || '',
                sub_rota: document.getElementById('filtro-sub-rota')?.value.trim() || '',
                data_pedido_de: document.getElementById('filtro-data-pedido-de')?.value.trim() || '',
                data_pedido_ate: document.getElementById('filtro-data-pedido-ate')?.value.trim() || '',
                data_entrega_de: document.getElementById('filtro-data-entrega-de')?.value.trim() || '',
                data_entrega_ate: document.getElementById('filtro-data-entrega-ate')?.value.trim() || '',
            };

            // 🚀 CRÍTICO: Remover campos vazios antes de salvar
            state.filtrosAplicados = {};
            Object.keys(filtrosTemp).forEach(key => {
                if (filtrosTemp[key] && filtrosTemp[key] !== '') {
                    state.filtrosAplicados[key] = filtrosTemp[key];
                }
            });

            console.log('📋 Filtros aplicados:', state.filtrosAplicados);

            // 🚀 OTIMIZAÇÃO: Salvar APENAS se houver filtros válidos
            try {
                if (Object.keys(state.filtrosAplicados).length > 0) {
                    localStorage.setItem('carteira_simples_filtros', JSON.stringify(state.filtrosAplicados));
                    console.log('✅ Filtros salvos no localStorage');
                } else {
                    localStorage.removeItem('carteira_simples_filtros');
                    console.log('🗑️ Nenhum filtro para salvar, localStorage limpo');
                }
            } catch (e) {
                console.warn('Erro ao salvar filtros no localStorage:', e);
            }

            state.paginaAtual = 1;
            state.projecaoEstoqueOffset = 0;
            carregarDados();
        } catch (erro) {
            console.error('Erro ao aplicar filtros:', erro);
            mostrarMensagem('Erro', 'Erro ao aplicar filtros. Verifique o console.', 'danger');
        }
    }

    function limparFiltros() {
        try {
            const filtroIds = [
                'filtro-busca', 'filtro-estado', 'filtro-municipio', 'filtro-rota', 'filtro-sub-rota',
                'filtro-data-pedido-de', 'filtro-data-pedido-ate',
                'filtro-data-entrega-de', 'filtro-data-entrega-ate'
            ];

            filtroIds.forEach(id => {
                const elemento = document.getElementById(id);
                if (elemento) elemento.value = '';
            });

            // 🚀 OTIMIZAÇÃO: Limpar filtros salvos no localStorage ANTES de limpar state
            try {
                localStorage.removeItem('carteira_simples_filtros');
                console.log('✅ Filtros limpos do localStorage');
            } catch (e) {
                console.warn('Erro ao limpar filtros do localStorage:', e);
            }

            state.filtrosAplicados = {};
            state.paginaAtual = 1;
            state.projecaoEstoqueOffset = 0; // 🆕 RESETAR offset global

            carregarDados();
        } catch (erro) {
            console.error('Erro ao limpar filtros:', erro);
            mostrarMensagem('Erro', 'Erro ao limpar filtros. Verifique o console.', 'danger');
        }
    }

    // 🚀 OTIMIZAÇÃO: Função para restaurar filtros salvos do localStorage
    function restaurarFiltrosSalvos() {
        try {
            const filtrosSalvos = localStorage.getItem('carteira_simples_filtros');
            if (!filtrosSalvos) {
                console.log('📋 Nenhum filtro salvo no localStorage');
                return;
            }

            const filtros = JSON.parse(filtrosSalvos);

            // ✅ VALIDAÇÃO: Verificar se filtros são válidos (não vazios)
            const temFiltroValido = Object.values(filtros).some(valor => valor && valor.trim() !== '');
            if (!temFiltroValido) {
                console.log('⚠️ Filtros salvos estão vazios, ignorando...');
                localStorage.removeItem('carteira_simples_filtros');
                return;
            }

            // Aplicar filtros nos inputs
            Object.keys(filtros).forEach(key => {
                const valor = filtros[key];
                if (!valor) return;

                // Mapear chaves para IDs dos inputs
                const mapeamento = {
                    'busca_geral': 'filtro-busca',  // 🆕 Busca geral
                    'num_pedido': 'filtro-busca',   // Compatibilidade com filtros antigos
                    'estado': 'filtro-estado',
                    'municipio': 'filtro-municipio',
                    'rota': 'filtro-rota',
                    'sub_rota': 'filtro-sub-rota',
                    'data_pedido_de': 'filtro-data-pedido-de',
                    'data_pedido_ate': 'filtro-data-pedido-ate',
                    'data_entrega_de': 'filtro-data-entrega-de',
                    'data_entrega_ate': 'filtro-data-entrega-ate'
                };

                const inputId = mapeamento[key];
                if (inputId) {
                    const input = document.getElementById(inputId);
                    if (input) {
                        input.value = valor;
                    }
                }
            });

            // Aplicar filtros no estado (sem chamar carregarDados, será chamado na inicialização)
            state.filtrosAplicados = filtros;

            console.log('✅ Filtros restaurados do localStorage:', filtros);
        } catch (erro) {
            console.warn('Erro ao restaurar filtros do localStorage:', erro);
        }
    }

    // 🆕 ATUALIZAR INDICADOR VISUAL DE FILTROS ATIVOS
    function atualizarIndicadorFiltros() {
        const btnLimparFiltros = document.getElementById('btn-limpar-filtros');
        const btnAplicarFiltros = document.getElementById('btn-aplicar-filtros');

        const temFiltros = Object.keys(state.filtrosAplicados).length > 0;

        if (temFiltros) {
            // 🔧 Adicionar badge visual no botão de limpar filtros
            if (btnLimparFiltros) {
                const qtdFiltros = Object.keys(state.filtrosAplicados).length;
                btnLimparFiltros.classList.add('btn-warning');
                btnLimparFiltros.classList.remove('btn-secondary');
                btnLimparFiltros.innerHTML = `
                    <i class="fas fa-times-circle"></i>
                    Limpar Filtros
                    <span class="badge bg-dark">${qtdFiltros}</span>
                `;
            }

            if (btnAplicarFiltros) {
                btnAplicarFiltros.classList.add('btn-success');
                btnAplicarFiltros.classList.remove('btn-primary');
            }

            console.log(`✅ ${Object.keys(state.filtrosAplicados).length} filtro(s) ativo(s)`);
        } else {
            // 🔧 Remover badge quando não há filtros
            if (btnLimparFiltros) {
                btnLimparFiltros.classList.remove('btn-warning');
                btnLimparFiltros.classList.add('btn-secondary');
                btnLimparFiltros.innerHTML = '<i class="fas fa-times-circle"></i> Limpar Filtros';
            }

            if (btnAplicarFiltros) {
                btnAplicarFiltros.classList.remove('btn-success');
                btnAplicarFiltros.classList.add('btn-primary');
            }
        }
    }

    // 🆕 POPULAR FILTROS DE ROTA E SUB-ROTA DINAMICAMENTE
    function popularFiltrosRotas() {
        try {
            // 🔧 CORREÇÃO: Só atualizar selects se houver dados
            // Se não há dados filtrados, preservar opções atuais
            if (!state.dados || state.dados.length === 0) {
                console.log('⚠️ Sem dados filtrados - preservando opções dos selects');
                return;
            }

            const rotas = new Set();
            const subRotas = new Set();

            // Coletar todas as rotas e sub-rotas únicas dos dados FILTRADOS
            state.dados.forEach(item => {
                if (item.rota) rotas.add(item.rota);
                if (item.sub_rota) subRotas.add(item.sub_rota);
            });

            // Popular select de Rota (APENAS se houver rotas nos dados)
            const selectRota = document.getElementById('filtro-rota');
            if (selectRota && rotas.size > 0) {
                // 🔧 PRESERVAR valor selecionado atual
                const valorAtual = selectRota.value;

                const rotasOrdenadas = Array.from(rotas).sort();
                selectRota.innerHTML = '<option value="">Rota</option>' +
                    rotasOrdenadas.map(r => `<option value="${r}">${r}</option>`).join('');

                // 🔧 RESTAURAR valor selecionado se ainda existir nas opções
                if (valorAtual && rotasOrdenadas.includes(valorAtual)) {
                    selectRota.value = valorAtual;
                }
            }

            // Popular select de Sub-rota (APENAS se houver sub-rotas nos dados)
            const selectSubRota = document.getElementById('filtro-sub-rota');
            if (selectSubRota && subRotas.size > 0) {
                // 🔧 PRESERVAR valor selecionado atual
                const valorAtual = selectSubRota.value;

                const subRotasOrdenadas = Array.from(subRotas).sort();
                selectSubRota.innerHTML = '<option value="">Sub-rota</option>' +
                    subRotasOrdenadas.map(sr => `<option value="${sr}">${sr}</option>`).join('');

                // 🔧 RESTAURAR valor selecionado se ainda existir nas opções
                if (valorAtual && subRotasOrdenadas.includes(valorAtual)) {
                    selectSubRota.value = valorAtual;
                }
            }

            console.log(`✅ Filtros atualizados: ${rotas.size} rotas, ${subRotas.size} sub-rotas`);
        } catch (erro) {
            console.error('Erro ao popular filtros de rotas:', erro);
        }
    }

    // ==============================================
    // RENDERIZAÇÃO DA TABELA (VIRTUAL SCROLLING)
    // ==============================================
    function renderizarTabela() {
        const tbody = document.getElementById('tbody-carteira');

        if (!state.dados || state.dados.length === 0) {
            // 🔧 CORREÇÃO: Mensagem de erro visual mais clara
            const temFiltrosAplicados = Object.keys(state.filtrosAplicados).length > 0;

            if (temFiltrosAplicados) {
                // Se há filtros aplicados mas não há dados = filtro não encontrou nada
                tbody.innerHTML = `
                    <tr>
                        <td colspan="29" class="text-center py-4">
                            <div class="alert alert-warning d-inline-block" role="alert">
                                <i class="fas fa-exclamation-triangle"></i>
                                <strong>Nenhum registro encontrado com os filtros aplicados</strong>
                                <br>
                                <small>Tente ajustar os critérios de busca ou limpar os filtros.</small>
                            </div>
                        </td>
                    </tr>
                `;
                console.warn('⚠️ Filtros aplicados mas nenhum dado encontrado:', state.filtrosAplicados);
            } else {
                // Se não há filtros e não há dados = carteira vazia
                tbody.innerHTML = '<tr><td colspan="29" class="text-center py-3">Nenhum registro encontrado na carteira</td></tr>';
            }
            return;
        }

        console.log(`🚀 Virtual Scrolling: ${state.dados.length} linhas (renderizando apenas primeiras 150)`);

        // Limpar tabela
        tbody.innerHTML = '';

        // 🆕 ATUALIZAR CABEÇALHO DE ESTOQUE COM DATAS DINÂMICAS
        atualizarCabecalhoEstoque();

        // 🚀 VIRTUAL SCROLLING: Renderizar APENAS primeiras 150 linhas
        const start = 0;
        const end = Math.min(150, state.dados.length);

        // Criar fragment
        const fragment = document.createDocumentFragment();
        const tempTable = document.createElement('table');
        const tempTbody = document.createElement('tbody');
        tempTable.appendChild(tempTbody);

        // Renderizar apenas linhas visíveis
        const html = state.dados.slice(start, end).map((item, relativeIndex) => {
            const absoluteIndex = start + relativeIndex;
            if (item.tipo === 'pedido') {
                return renderizarLinha(item, absoluteIndex);
            } else if (item.tipo === 'separacao') {
                return renderizarLinhaSeparacao(item, absoluteIndex);
            }
            return '';
        }).join('');

        tempTbody.innerHTML = html;
        while (tempTbody.firstChild) {
            fragment.appendChild(tempTbody.firstChild);
        }

        tbody.appendChild(fragment);

        // Renderizar estoques das linhas visíveis
        for (let i = start; i < end; i++) {
            try {
                renderizarEstoquePrecalculado(i, state.dados[i]);
            } catch (erro) {
                console.error(`Erro ao renderizar estoque ${i}:`, erro);
            }
        }

        // Aplicar classes visuais e tooltips
        aplicarClassesVisuais();
        inicializarTooltips();

        // 🆕 APLICAR VISIBILIDADE INICIAL (ocultar pedidos com saldo=0 após carregamento)
        aplicarVisibilidadeInicial();

        // 🚀 Configurar scroll listener para carregar mais linhas sob demanda
        setupVirtualScrollListener();

        console.log(`✅ Renderização inicial: ${end} de ${state.dados.length} linhas`);
    }

    // 🚀 VIRTUAL SCROLLING: Listener de scroll
    function setupVirtualScrollListener() {
        const tableContainer = document.querySelector('.table-responsive');
        if (!tableContainer) {
            console.warn('⚠️ .table-responsive não encontrado para virtual scroll');
            return;
        }

        let scrollTimeout = null;

        tableContainer.addEventListener('scroll', function() {
            // Debounce scroll
            if (scrollTimeout) clearTimeout(scrollTimeout);

            scrollTimeout = setTimeout(() => {
                const scrollTop = tableContainer.scrollTop;
                const scrollHeight = tableContainer.scrollHeight;
                const clientHeight = tableContainer.clientHeight;

                // Se scrollou até 80% da página, carregar mais linhas
                const scrollPercent = (scrollTop + clientHeight) / scrollHeight;

                if (scrollPercent > 0.8) {
                    carregarMaisLinhas();
                }
            }, 100);
        });

        console.log('✅ Virtual scroll listener configurado');
    }

    // 🚀 Carregar mais linhas sob demanda
    function carregarMaisLinhas() {
        const tbody = document.getElementById('tbody-carteira');
        const currentRendered = tbody.querySelectorAll('tr').length;

        if (currentRendered >= state.dados.length) {
            console.log('✅ Todas as linhas já foram renderizadas');
            return;
        }

        const nextBatch = Math.min(currentRendered + 100, state.dados.length);
        console.log(`🔄 Carregando mais linhas: ${currentRendered} → ${nextBatch}`);

        const fragment = document.createDocumentFragment();
        const tempTable = document.createElement('table');
        const tempTbody = document.createElement('tbody');
        tempTable.appendChild(tempTbody);

        // Renderizar próximo lote
        const html = state.dados.slice(currentRendered, nextBatch).map((item, relativeIndex) => {
            const absoluteIndex = currentRendered + relativeIndex;
            if (item.tipo === 'pedido') {
                return renderizarLinha(item, absoluteIndex);
            } else if (item.tipo === 'separacao') {
                return renderizarLinhaSeparacao(item, absoluteIndex);
            }
            return '';
        }).join('');

        tempTbody.innerHTML = html;
        while (tempTbody.firstChild) {
            fragment.appendChild(tempTbody.firstChild);
        }

        tbody.appendChild(fragment);

        // Renderizar estoques do novo lote
        for (let i = currentRendered; i < nextBatch; i++) {
            try {
                renderizarEstoquePrecalculado(i, state.dados[i]);
            } catch (erro) {
                console.error(`Erro ao renderizar estoque ${i}:`, erro);
            }
        }

        console.log(`✅ ${nextBatch} de ${state.dados.length} linhas renderizadas`);
    }

    // 🆕 FUNÇÃO PARA APLICAR CLASSES VISUAIS (bordas - cor já aplicada na renderização)
    function aplicarClassesVisuais() {
        let pedidoAnterior = null;
        let loteAnterior = null;

        state.dados.forEach((item, index) => {
            const row = document.getElementById(item.tipo === 'separacao' ? `row-sep-${index}` : `row-${index}`);
            if (!row) return;

            // 🆕 SEPARADORES VISUAIS
            // Linha GROSSA ao mudar de num_pedido
            if (pedidoAnterior !== null && item.num_pedido !== pedidoAnterior) {
                row.classList.add('border-pedido-top');
            }

            // Linha MÉDIA ao mudar de separacao_lote_id (dentro do mesmo pedido)
            if (item.tipo === 'separacao' &&
                item.num_pedido === pedidoAnterior &&
                loteAnterior !== null &&
                item.separacao_lote_id !== loteAnterior) {
                row.classList.add('border-lote-top');
            }

            // Atualizar rastreamento
            pedidoAnterior = item.num_pedido;
            loteAnterior = item.separacao_lote_id || null;
        });
    }

    // 🆕 FUNÇÃO PARA ATUALIZAR CABEÇALHO DE ESTOQUE COM DATAS DINÂMICAS (28 DIAS)
    function atualizarCabecalhoEstoque() {
        const headerDatas = document.getElementById('estoque-header-datas');
        if (!headerDatas) return;

        const hoje = new Date();
        const diasHTML = [];

        // ✅ MOSTRAR TODOS OS 28 DIAS (sem offset - remoção de navegação)
        for (let i = 0; i < 28; i++) {
            const dia = new Date(hoje);
            dia.setDate(hoje.getDate() + i);

            const diaMes = String(dia.getDate()).padStart(2, '0');
            const mes = String(dia.getMonth() + 1).padStart(2, '0');
            const diaSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'][dia.getDay()];

            diasHTML.push(`
                <span class="estoque-header-dia" title="${diaSemana} ${diaMes}/${mes}">
                    <div style="font-size: 9px; font-weight: 700;">D${i}</div>
                    <div style="font-size: 7px;">${diaMes}/${mes}</div>
                </span>
            `);
        }

        headerDatas.innerHTML = diasHTML.join('');
    }

    // 🆕 FUNÇÃO PARA RENDERIZAR LINHA DE SEPARAÇÃO
    function renderizarLinhaSeparacao(item, index) {
        const rowId = `row-sep-${index}`;
        const qtdEditId = `qtd-sep-${index}`;
        const dtExpedId = `dt-exped-sep-${index}`;
        const dtAgendId = `dt-agend-sep-${index}`;
        const protocoloId = `protocolo-sep-${index}`;

        // Truncar textos
        const razaoSocialTrunc = truncarTexto(item.raz_social_red || '', 30);
        const municipioTrunc = truncarTexto(item.municipio || '', 20);
        const nomeProdutoTrunc = truncarTexto(item.nome_produto || '', 50);

        // 🆕 CORES BASEADAS EM STATUS - USANDO CLASSES BOOTSTRAP
        let classesCor = '';

        // 🔴 1. PRIORIZAR SEPARAÇÃO ATRASADA (verificar PRIMEIRO)
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        const dataExpedicao = item.expedicao ? new Date(item.expedicao + 'T00:00:00') : null;
        const isAtrasada = dataExpedicao && dataExpedicao < hoje;

        if (isAtrasada) {
            classesCor = 'separacao-atrasada'; // ✅ VERMELHO - PRIORIDADE MÁXIMA
        } else if (item.status_calculado === 'ABERTO') {
            classesCor = 'table-warning'; // Amarelo Bootstrap
        } else if (item.status_calculado === 'COTADO') {
            classesCor = 'table-info'; // Azul Bootstrap
        }

        return `
            <tr id="${rowId}"
                class="${classesCor}"
                data-tipo="separacao"
                data-separacao-id="${item.separacao_id}"
                data-num-pedido="${item.num_pedido}"
                data-cod-produto="${item.cod_produto}"
                data-palletizacao="${item.palletizacao}"
                data-peso-bruto="${item.peso_bruto}"
                data-preco="${item.preco_produto_pedido}"
                data-qtd-saldo="${item.qtd_saldo}">

                <!-- Dados básicos -->
                <td>${item.num_pedido}</td>
                <td>${item.pedido_cliente || ''}</td>
                <td>${item.data_pedido ? new Date(item.data_pedido + 'T00:00:00').toLocaleDateString('pt-BR') : ''}</td>
                <td>${item.data_entrega_pedido ? new Date(item.data_entrega_pedido + 'T00:00:00').toLocaleDateString('pt-BR') : ''}</td>
                <td>${item.cnpj_cpf}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.raz_social_red || ''}">
                        ${razaoSocialTrunc}
                    </span>
                </td>
                <td>${item.estado || ''}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.municipio || ''}">
                        ${municipioTrunc}
                    </span>
                </td>
                <td>${item.cod_produto}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.nome_produto || ''}">
                        ${nomeProdutoTrunc}
                    </span>
                </td>

                <!-- Quantidades e valores - QTD EDITÁVEL -->
                <td class="text-end">
                    <input type="number" class="form-control form-control-sm qtd-separacao-editavel"
                        id="${qtdEditId}"
                        data-row-index="${index}"
                        data-separacao-id="${item.separacao_id}"
                        min="0"
                        step="0.01"
                        value="${Math.round(item.qtd_saldo || 0)}"
                        style="width: 60px; padding: 1px 3px;">
                </td>
                <td class="text-end valor-total">R$ ${Math.round(item.valor_total || 0).toLocaleString('pt-BR')}</td>
                <td class="text-end pallets">${(item.pallets || 0).toFixed(2)}</td>
                <td class="text-end peso">${Math.round(item.peso || 0)}</td>

                <!-- Rota -->
                <td>${item.rota || ''}</td>
                <td>${item.sub_rota || ''}</td>

                <!-- Estoque projetado (PRÉ-CALCULADO) -->
                <td class="text-end est-data-edit" id="est-data-${index}" data-estoque-original="${item.estoque_atual || 0}">
                    -
                </td>
                <td class="text-end menor-est-7d" id="menor-7d-${index}" data-menor-original="${item.menor_estoque_d7 || 0}">
                    ${item.menor_estoque_d7 !== undefined ? Math.round(item.menor_estoque_d7) : '-'}
                </td>

                <!-- Botão OK - DESABILITADO para separações -->
                <td class="text-center">
                    <button type="button" class="btn btn-secondary btn-sm-custom" disabled title="Separação já criada">
                        -
                    </button>
                </td>

                <!-- Ações rápidas - DESABILITADAS para separações -->
                <td class="text-center">
                    <span class="text-muted" style="font-size: 9px;">-</span>
                </td>

                <!-- Campos editáveis - QTD EDIT TAMBÉM EDITÁVEL -->
                <td>
                    <input type="number" class="form-control form-control-sm qtd-separacao-editavel-2"
                        data-row-index="${index}"
                        data-separacao-id="${item.separacao_id}"
                        min="0"
                        step="0.01"
                        value="${Math.round(item.qtd_saldo || 0)}"
                        style="padding: 1px 3px;">
                </td>

                <td class="text-center">
                    <button type="button" class="btn btn-warning btn-sm-custom btn-d1"
                        data-row-index="${index}" title="Adicionar +1 dia útil">
                        D1
                    </button>
                </td>

                <td>
                    <input type="date" class="form-control form-control-sm dt-expedicao"
                        id="${dtExpedId}"
                        data-row-index="${index}"
                        value="${item.expedicao || ''}">
                </td>

                <td>
                    <input type="date" class="form-control form-control-sm dt-agendamento"
                        id="${dtAgendId}"
                        value="${item.agendamento || ''}">
                </td>

                <td>
                    <input type="text" class="form-control form-control-sm protocolo"
                        id="${protocoloId}"
                        maxlength="50"
                        value="${item.protocolo || ''}">
                </td>

                <!-- Botão confirmar agendamento -->
                <td class="text-center">
                    <button type="button" class="btn ${item.agendamento_confirmado ? 'btn-success' : 'btn-primary'} btn-sm-custom btn-confirmar"
                        data-row-index="${index}"
                        ${item.agendamento_confirmado ? 'disabled' : ''}
                        title="${item.agendamento_confirmado ? 'Já confirmado' : 'Confirmar agendamento (protocolo necessário)'}">
                        ${item.agendamento_confirmado ? '✓' : '⏱'}
                    </button>
                </td>

                <!-- Estoque atual e carteira -->
                <td class="text-end">${Math.round(item.estoque_atual || 0)}</td>
                <td class="text-end">${Math.round(item.qtd_carteira || 0)}</td>

                <!-- Projeção D0-D28 -->
                <td class="estoque-projecao" id="projecao-${index}">
                    <div class="d-flex gap-1 flex-nowrap" id="projecao-dias-${index}" style="min-width: 1200px; overflow-x: visible;">
                        ${Array(28).fill('<span class="estoque-dia">-</span>').join('')}
                    </div>
                </td>
            </tr>
        `;
    }

    function renderizarLinha(item, index) {
        const rowId = `row-${index}`;
        const qtdEditId = `qtd-edit-${index}`;
        const dtExpedId = `dt-exped-${index}`;
        const dtAgendId = `dt-agend-${index}`;
        const protocoloId = `protocolo-${index}`;

        // Truncar textos
        const razaoSocialTrunc = truncarTexto(item.raz_social_red || '', 30);
        const municipioTrunc = truncarTexto(item.municipio || '', 20);
        const nomeProdutoTrunc = truncarTexto(item.nome_produto || '', 50);

        return `
            <tr id="${rowId}"
                data-num-pedido="${item.num_pedido}"
                data-cod-produto="${item.cod_produto}"
                data-palletizacao="${item.palletizacao}"
                data-peso-bruto="${item.peso_bruto}"
                data-preco="${item.preco_produto_pedido}"
                data-qtd-saldo="${item.qtd_saldo}">

                <!-- Dados básicos -->
                <td>${item.num_pedido}</td>
                <td>${item.pedido_cliente || ''}</td>
                <td>${item.data_pedido ? new Date(item.data_pedido + 'T00:00:00').toLocaleDateString('pt-BR') : ''}</td>
                <td>${item.data_entrega_pedido ? new Date(item.data_entrega_pedido + 'T00:00:00').toLocaleDateString('pt-BR') : ''}</td>
                <td>${item.cnpj_cpf}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.raz_social_red || ''}">
                        ${razaoSocialTrunc}
                    </span>
                </td>
                <td>${item.estado || ''}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.municipio || ''}">
                        ${municipioTrunc}
                    </span>
                </td>
                <td>${item.cod_produto}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.nome_produto || ''}">
                        ${nomeProdutoTrunc}
                    </span>
                </td>

                <!-- Quantidades e valores -->
                <td class="text-end">${Math.round(item.qtd_saldo || 0)}</td>
                <td class="text-end valor-total">R$ ${Math.round(item.valor_total || 0).toLocaleString('pt-BR')}</td>
                <td class="text-end pallets">${(item.pallets || 0).toFixed(2)}</td>
                <td class="text-end peso">${Math.round(item.peso || 0)}</td>

                <!-- Rota -->
                <td>${item.rota || ''}</td>
                <td>${item.sub_rota || ''}</td>

                <!-- Estoque projetado (PRÉ-CALCULADO) -->
                <td class="text-end est-data-edit" id="est-data-${index}" data-estoque-original="${item.estoque_atual || 0}">
                    -
                </td>
                <td class="text-end menor-est-7d" id="menor-7d-${index}" data-menor-original="${item.menor_estoque_d7 || 0}">
                    ${item.menor_estoque_d7 !== undefined ? Math.round(item.menor_estoque_d7) : '-'}
                </td>

                <!-- Botão OK -->
                <td class="text-center">
                    <button type="button" class="btn btn-success btn-sm-custom btn-ok"
                        data-row-index="${index}">
                        OK
                    </button>
                </td>

                <!-- Ações rápidas -->
                <td class="text-center">
                    <button type="button" class="btn btn-primary btn-sm-custom btn-add-qtd"
                        data-row-index="${index}" title="Adicionar qtd_saldo">
                        →
                    </button>
                    <button type="button" class="btn btn-info btn-sm-custom btn-add-all"
                        data-row-index="${index}" title="Adicionar todos os produtos">
                        »
                    </button>
                </td>

                <!-- Campos editáveis -->
                <td>
                    <input type="number" class="form-control form-control-sm qtd-editavel"
                        id="${qtdEditId}"
                        data-row-index="${index}"
                        min="0"
                        max="${item.qtd_saldo}"
                        step="0.01"
                        value="0">
                </td>

                <td class="text-center">
                    <button type="button" class="btn btn-warning btn-sm-custom btn-d1"
                        data-row-index="${index}" title="Adicionar +1 dia útil">
                        D1
                    </button>
                </td>

                <td>
                    <input type="date" class="form-control form-control-sm dt-expedicao"
                        id="${dtExpedId}"
                        data-row-index="${index}"
                        value="${item.expedicao || ''}">
                </td>

                <td>
                    <input type="date" class="form-control form-control-sm dt-agendamento"
                        id="${dtAgendId}"
                        value="${item.agendamento || ''}">
                </td>

                <td>
                    <input type="text" class="form-control form-control-sm protocolo"
                        id="${protocoloId}"
                        maxlength="50"
                        value="${item.protocolo || ''}">
                </td>

                <!-- Botão confirmar agendamento -->
                <td class="text-center">
                    <button type="button" class="btn ${item.agendamento_confirmado ? 'btn-success' : 'btn-primary'} btn-sm-custom btn-confirmar"
                        data-row-index="${index}"
                        ${item.agendamento_confirmado ? 'disabled' : ''}
                        title="${item.agendamento_confirmado ? 'Já confirmado' : 'Confirmar agendamento (protocolo necessário)'}">
                        ${item.agendamento_confirmado ? '✓' : '⏱'}
                    </button>
                </td>

                <!-- Estoque atual e carteira -->
                <td class="text-end">${Math.round(item.estoque_atual || 0)}</td>
                <td class="text-end">${Math.round(item.qtd_carteira || 0)}</td>

                <!-- Projeção D0-D28 -->
                <td class="estoque-projecao" id="projecao-${index}">
                    <div class="d-flex gap-1 flex-nowrap" id="projecao-dias-${index}" style="min-width: 1200px; overflow-x: visible;">
                        ${Array(28).fill('<span class="estoque-dia">-</span>').join('')}
                    </div>
                </td>
            </tr>
        `;
    }

    // ==============================================
    // HANDLERS DE EVENTOS
    // ==============================================
    function handleTableClick(e) {
        const target = e.target;

        // Botão OK
        if (target.classList.contains('btn-ok')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            gerarSeparacao(rowIndex);
        }

        // Botão adicionar qtd
        else if (target.classList.contains('btn-add-qtd')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            adicionarQtdSaldo(rowIndex);
        }

        // Botão adicionar todos
        else if (target.classList.contains('btn-add-all')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            adicionarTodosProdutos(rowIndex);
        }

        // Botão D1
        else if (target.classList.contains('btn-d1')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            adicionarDiaUtil(rowIndex);
        }

        // Botão confirmar
        else if (target.classList.contains('btn-confirmar')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            confirmarAgendamento(rowIndex);
        }

        // Navegação de estoque
        else if (target.classList.contains('btn-prev-dia')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            navegarEstoque(rowIndex, -1);
        }
        else if (target.classList.contains('btn-next-dia')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            navegarEstoque(rowIndex, 1);
        }
    }

    async function handleTableChange(e) {
        const target = e.target;

        // Mudança na data de expedição
        if (target.classList.contains('dt-expedicao')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const item = state.dados[rowIndex];
            const novoValor = target.value;
            const colunaEditada = 'expedicao';

            // 🆕 DETECTAR SE É SEPARAÇÃO OU CARTEIRA
            const isSeparacao = item.tipo === 'separacao';
            const separacaoLoteId = item.separacao_lote_id;

            // 🆕 Se mudou data de uma separação com lote, atualizar todo o lote NO BACKEND
            if (isSeparacao && separacaoLoteId && colunaEditada === 'expedicao') {
                await atualizarDataSeparacaoLote(separacaoLoteId, novoValor);
            } else if (!isSeparacao && colunaEditada === 'expedicao') {
                // Se mudou data de um item da CarteiraPrincipal, atualizar NO BACKEND
                await atualizarItemCarteira(item.id, colunaEditada, novoValor);
            }

            // Recalcular TODAS as linhas do mesmo produto (atualiza UI)
            recalcularTodasLinhasProduto(item.cod_produto);
        }
    }

    function handleTableInput(e) {
        const target = e.target;

        // Mudança na quantidade editável de PEDIDO
        if (target.classList.contains('qtd-editavel')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const item = state.dados[rowIndex];

            // Recalcular valores da linha (valor total, pallets, peso)
            recalcularValoresLinha(rowIndex);

            // Recalcular TODAS as linhas do mesmo produto
            recalcularTodasLinhasProduto(item.cod_produto);
        }

        // 🆕 Mudança na quantidade editável de SEPARAÇÃO
        if (target.classList.contains('qtd-separacao-editavel') || target.classList.contains('qtd-separacao-editavel-2')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const separacaoId = parseInt(target.dataset.separacaoId);
            const novaQtd = parseFloat(target.value) || 0;

            // Debounce para evitar múltiplas chamadas
            clearTimeout(target.debounceTimer);
            target.debounceTimer = setTimeout(() => {
                atualizarQtdSeparacao(separacaoId, novaQtd, rowIndex);
            }, 500); // 500ms de delay
        }
    }

    // ==============================================
    // VISIBILIDADE DE LINHAS (OCULTAR/REMOVER/REEXIBIR)
    // ==============================================

    /**
     * Aplica visibilidade inicial para TODOS os pedidos após carregamento
     * (oculta pedidos com saldo=0, não remove separações pois vêm corretas do backend)
     */
    function aplicarVisibilidadeInicial() {
        console.log('🔍 Aplicando visibilidade inicial para todos os pedidos...');

        let pedidosOcultados = 0;

        state.dados.forEach((item, index) => {
            if (item.tipo === 'pedido') {
                // ✅ CORREÇÃO: Usar qtd_saldo que já vem calculado da API
                // API já faz: qtd_saldo = qtd_saldo_produto_pedido - qtd_separada
                const saldoAtual = parseFloat(item.qtd_saldo) || 0;

                if (saldoAtual === 0) {
                    // OCULTAR pedido com saldo=0
                    const row = document.getElementById(`row-${index}`);
                    if (row) {
                        row.style.display = 'none';
                        pedidosOcultados++;
                        console.log(`👻 Ocultando Pedido ${item.num_pedido} - ${item.cod_produto} (saldo=0)`);
                    } else {
                        console.warn(`⚠️ Linha row-${index} não encontrada no DOM para Pedido ${item.num_pedido}`);
                    }
                }
            }
        });

        if (pedidosOcultados > 0) {
            console.log(`👻 ${pedidosOcultados} pedido(s) ocultado(s) por saldo=0`);
        } else {
            console.log('✅ Nenhum pedido com saldo=0 encontrado');
        }
    }

    /**
     * Verifica e aplica regras de visibilidade para linhas de Pedido
     *
     * REGRAS:
     * 1. Pedido com saldo=0 → OCULTAR (display:none) - manter em state.dados
     * 2. Pedido com saldo>0 → REEXIBIR (remover display:none)
     *
     * NOTA: Separações com qtd=0 são DELETADAS pelo backend, não precisam de lógica aqui
     *
     * @param {string} codProduto - Código do produto afetado
     * @param {string} numPedido - Número do pedido afetado
     */
    function verificarVisibilidadeLinhas(codProduto, numPedido) {
        console.log(`🔍 Verificando visibilidade: Pedido=${numPedido}, Produto=${codProduto}`);

        // VERIFICAR E OCULTAR/REEXIBIR PEDIDOS COM SALDO=0
        state.dados.forEach((item, index) => {
            if (item.tipo === 'pedido' &&
                item.num_pedido === numPedido &&
                item.cod_produto === codProduto) {

                // ✅ CORREÇÃO: Recalcular saldo atual baseado nos dados atuais do state
                // (necessário pois separações podem ter sido editadas)
                const totalSeparado = state.dados
                    .filter(d => d.tipo === 'separacao' &&
                                d.num_pedido === numPedido &&
                                d.cod_produto === codProduto)
                    .reduce((sum, sep) => sum + (parseFloat(sep.qtd_saldo) || 0), 0);

                const saldoAtual = (item.qtd_original_pedido || 0) - totalSeparado;

                // ✅ ATUALIZAR qtd_saldo no state para refletir mudança
                item.qtd_saldo = saldoAtual;

                const row = document.getElementById(`row-${index}`);
                if (row) {
                    // Atualizar atributo data-qtd-saldo no DOM
                    row.setAttribute('data-qtd-saldo', saldoAtual);

                    if (saldoAtual === 0) {
                        // OCULTAR (display:none)
                        row.style.display = 'none';
                        console.log(`👻 Ocultada linha de Pedido: ${numPedido} - ${codProduto} (saldo=0)`);
                    } else if (saldoAtual > 0) {
                        // REEXIBIR (remover display:none)
                        if (row.style.display === 'none') {
                            row.style.display = '';
                            console.log(`👁️ Reexibida linha de Pedido: ${numPedido} - ${codProduto} (saldo=${saldoAtual})`);
                        }
                    }
                }
            }
        });
    }

    // ==============================================
    // AÇÕES DE BOTÕES
    // ==============================================

    // 🆕 FUNÇÃO PARA ATUALIZAR QTD DE SEPARAÇÃO VIA API
    async function atualizarQtdSeparacao(separacaoId, novaQtd, rowIndex) {
        try {
            const item = state.dados[rowIndex];

            // Validação básica
            if (!item || item.tipo !== 'separacao') {
                console.error('Item não é uma separação válida');
                return;
            }

            // Chamar API
            const response = await fetch('/carteira/simples/api/atualizar-qtd-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    separacao_id: separacaoId,
                    nova_qtd: novaQtd
                })
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao atualizar quantidade');
            }

            // 🆕 SE SEPARAÇÃO FOI DELETADA (qtd=0) → Remover do DOM e state, depois recarregar
            if (resultado.deletado) {
                console.log(`🗑️ Separação ID=${separacaoId} DELETADA do backend (qtd=0)`);

                // Remover linha do DOM
                const row = document.getElementById(`row-sep-${rowIndex}`);
                if (row) {
                    row.remove();
                    console.log(`✅ Linha removida do DOM`);
                }

                // Remover do state.dados
                state.dados.splice(rowIndex, 1);
                console.log(`✅ Item removido do state.dados`);

                // Atualizar qtd do pedido correspondente (deduzir)
                atualizarQtdPedidoAposEdicaoSeparacao(item.num_pedido, item.cod_produto);

                // Verificar se pedido ficou com saldo=0 e ocultar
                verificarVisibilidadeLinhas(item.cod_produto, item.num_pedido);

                // Recarregar dados do backend para atualizar estoques D0-D28
                carregarDados();

                console.log(`✅ Separação deletada e dados recarregados`);
                return; // Sair da função
            }

            // SE NÃO FOI DELETADA (qtd > 0) → Atualizar dados locais normalmente
            // Atualizar dados locais
            item.qtd_saldo = resultado.separacao.qtd_saldo;
            item.valor_total = resultado.separacao.valor_saldo;
            item.pallets = resultado.separacao.pallet;
            item.peso = resultado.separacao.peso;

            // Atualizar UI da linha
            const row = document.getElementById(`row-sep-${rowIndex}`);
            if (row) {
                row.querySelector('.valor-total').textContent = formatarMoeda(item.valor_total);
                row.querySelector('.pallets').textContent = formatarNumero(item.pallets, 2);
                row.querySelector('.peso').textContent = Math.round(item.peso);
            }

            // Sincronizar os dois inputs de qtd
            const input1 = document.getElementById(`qtd-sep-${rowIndex}`);
            const input2 = row?.querySelector('.qtd-separacao-editavel-2');
            if (input1) input1.value = Math.round(item.qtd_saldo);
            if (input2) input2.value = Math.round(item.qtd_saldo);

            // Atualizar qtd do pedido correspondente (deduzir)
            atualizarQtdPedidoAposEdicaoSeparacao(item.num_pedido, item.cod_produto);

            // 🆕 VERIFICAR VISIBILIDADE (ocultar Pedido se saldo=0, reexibir se saldo>0)
            verificarVisibilidadeLinhas(item.cod_produto, item.num_pedido);

            // 🔧 CORREÇÃO: Recarregar dados do backend para atualizar saidas_previstas
            // Isso garante que ESTOQUE D0-D28 seja recalculado com as novas separações
            carregarDados();

            console.log(`✅ Quantidade da separação ${separacaoId} atualizada para ${novaQtd}`);

        } catch (erro) {
            console.error('Erro ao atualizar quantidade separação:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        }
    }

    // 🆕 FUNÇÃO PARA ATUALIZAR QTD DO PEDIDO APÓS EDIÇÃO DE SEPARAÇÃO
    function atualizarQtdPedidoAposEdicaoSeparacao(numPedido, codProduto) {
        // Encontrar linha do pedido
        state.dados.forEach((item, index) => {
            if (item.tipo === 'pedido' && item.num_pedido === numPedido && item.cod_produto === codProduto) {
                // Somar todas as qtds das separações deste pedido+produto
                const totalSeparado = state.dados
                    .filter(d => d.tipo === 'separacao' && d.num_pedido === numPedido && d.cod_produto === codProduto)
                    .reduce((sum, sep) => sum + (parseFloat(sep.qtd_saldo) || 0), 0);

                // 🔧 CORREÇÃO: Usar qtd_original_pedido (QTD DESTE PEDIDO, não soma de todos)
                const qtdOriginal = item.qtd_original_pedido;
                const novaQtdSaldo = qtdOriginal - totalSeparado;

                // Atualizar estado
                item.qtd_saldo = novaQtdSaldo;

                // Atualizar UI
                const row = document.getElementById(`row-${index}`);
                if (row) {
                    // Atualizar coluna Qtd
                    const tdQtd = row.children[10]; // Coluna 11 (índice 10)
                    if (tdQtd) {
                        tdQtd.textContent = Math.round(novaQtdSaldo);
                    }
                }

                // Recalcular valores da linha do pedido
                recalcularValoresLinha(index);
            }
        });
    }

    function adicionarQtdSaldo(rowIndex) {
        const item = state.dados[rowIndex];
        const inputQtd = document.getElementById(`qtd-edit-${rowIndex}`);
        inputQtd.value = item.qtd_saldo;

        // Recalcular valores da linha (valor total, pallets, peso)
        recalcularValoresLinha(rowIndex);

        // Recalcular estoques de TODAS as linhas do mesmo produto
        recalcularTodasLinhasProduto(item.cod_produto);
    }

    function adicionarTodosProdutos(rowIndex) {
        const item = state.dados[rowIndex];
        const numPedido = item.num_pedido;

        // Coletar todos os produtos únicos afetados
        const produtosAfetados = new Set();

        // Encontrar todos os produtos do mesmo pedido
        state.dados.forEach((d, idx) => {
            if (d.num_pedido === numPedido) {
                const inputQtd = document.getElementById(`qtd-edit-${idx}`);
                if (inputQtd) {
                    inputQtd.value = d.qtd_saldo;
                    recalcularValoresLinha(idx);
                    produtosAfetados.add(d.cod_produto);
                }
            }
        });

        // Recalcular estoques para cada produto afetado
        produtosAfetados.forEach(codProduto => {
            recalcularTodasLinhasProduto(codProduto);
        });

        mostrarMensagem('Sucesso', `Todas as quantidades do pedido ${numPedido} foram adicionadas`, 'success');
    }

    async function adicionarDiaUtil(rowIndex) {
        const item = state.dados[rowIndex];
        const inputId = item.tipo === 'separacao' ? `dt-exped-sep-${rowIndex}` : `dt-exped-${rowIndex}`;
        const inputData = document.getElementById(inputId);
        const dataAtual = inputData.value ? new Date(inputData.value + 'T00:00:00') : new Date();

        // Adicionar 1 dia
        dataAtual.setDate(dataAtual.getDate() + 1);

        // Se cair no fim de semana, avançar para segunda
        const diaSemana = dataAtual.getDay();
        if (diaSemana === 0) { // Domingo
            dataAtual.setDate(dataAtual.getDate() + 1);
        } else if (diaSemana === 6) { // Sábado
            dataAtual.setDate(dataAtual.getDate() + 2);
        }

        const novaData = dataAtual.toISOString().split('T')[0];
        inputData.value = novaData;

        // 🆕 Se for separação, atualizar TODOS os produtos do mesmo lote NO BACKEND
        if (item.tipo === 'separacao' && item.separacao_lote_id) {
            await atualizarDataSeparacaoLote(item.separacao_lote_id, novaData);
        } else {
            // 🆕 Se for item da CarteiraPrincipal, atualizar NO BACKEND
            await atualizarItemCarteira(item.id, 'expedicao', novaData);

            // Recalcular TODAS as linhas do mesmo produto (atualiza UI)
            recalcularTodasLinhasProduto(item.cod_produto);
        }
    }

    // 🆕 FUNÇÃO PARA ATUALIZAR DATA DE TODOS OS PRODUTOS DE UM LOTE DE SEPARAÇÃO
    async function atualizarDataSeparacaoLote(separacaoLoteId, novaData) {
        try {
            // 🔴 CHAMAR BACKEND PARA ATUALIZAR BANCO DE DADOS E RECALCULAR ESTOQUE
            const response = await fetch('/carteira/simples/api/atualizar-separacao-lote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    separacao_lote_id: separacaoLoteId,
                    expedicao: novaData
                })
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao atualizar data do lote');
            }

            console.log(`✅ Backend: ${resultado.message}`);

            // 🔄 ATUALIZAR FRONTEND (UI e estado local)
            const produtosAfetados = new Set();

            state.dados.forEach((d, idx) => {
                if (d.tipo === 'separacao' && d.separacao_lote_id === separacaoLoteId) {
                    // Atualizar input de data
                    const inputDataId = `dt-exped-sep-${idx}`;
                    const inputData = document.getElementById(inputDataId);
                    if (inputData) {
                        inputData.value = novaData;
                    }

                    // Atualizar estado
                    d.expedicao = novaData;

                    // 🆕 Atualizar estoque se veio do backend
                    if (resultado.estoque_atualizado && resultado.estoque_atualizado[d.cod_produto]) {
                        const estoqueNovo = resultado.estoque_atualizado[d.cod_produto];
                        d.estoque_atual = estoqueNovo.estoque_atual;
                        d.menor_estoque_d7 = estoqueNovo.menor_estoque_d7;
                        d.projecoes_estoque = estoqueNovo.projecoes;
                    }

                    // Adicionar produto à lista de afetados
                    produtosAfetados.add(d.cod_produto);
                }
            });

            // Recalcular estoques para cada produto afetado (atualiza UI)
            produtosAfetados.forEach(codProduto => {
                recalcularTodasLinhasProduto(codProduto);
            });

            console.log(`✅ Frontend: Data atualizada para ${produtosAfetados.size} produtos do lote ${separacaoLoteId}`);

        } catch (erro) {
            console.error('Erro ao atualizar data do lote:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        }
    }

    // 🆕 FUNÇÃO PARA ATUALIZAR ITEM DA CARTEIRAPRINCIPAL
    async function atualizarItemCarteira(itemId, campo, valor) {
        try {
            // 🔴 CHAMAR BACKEND PARA ATUALIZAR BANCO DE DADOS E RECALCULAR ESTOQUE
            const response = await fetch('/carteira/simples/api/atualizar-item-carteira', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: itemId,
                    campo: campo,
                    valor: valor
                })
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao atualizar item da carteira');
            }

            console.log(`✅ Backend: ${resultado.message}`);

            // 🆕 Atualizar estoque no estado local se veio do backend
            if (resultado.estoque_atualizado) {
                state.dados.forEach(d => {
                    if (d.id === itemId && d.tipo === 'pedido') {
                        d.estoque_atual = resultado.estoque_atualizado.estoque_atual;
                        d.menor_estoque_d7 = resultado.estoque_atualizado.menor_estoque_d7;
                        d.projecoes_estoque = resultado.estoque_atualizado.projecoes;
                    }
                });
            }

        } catch (erro) {
            console.error('Erro ao atualizar item da carteira:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        }
    }

    async function confirmarAgendamento(rowIndex) {
        const item = state.dados[rowIndex];
        const protocolo = document.getElementById(`protocolo-${rowIndex}`).value.trim();

        if (!protocolo) {
            mostrarMensagem('Atenção', 'Protocolo é obrigatório para confirmação', 'warning');
            return;
        }

        try {
            mostrarLoading(true);

            const response = await fetch('/carteira/simples/api/confirmar-agendamento', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: item.num_pedido,
                    cod_produto: item.cod_produto,
                    protocolo: protocolo
                })
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao confirmar agendamento');
            }

            mostrarMensagem('Sucesso', resultado.message, 'success');

            // Atualizar estado e UI do botão
            state.dados[rowIndex].agendamento_confirmado = true;

            const btnConfirmar = document.querySelector(`button.btn-confirmar[data-row-index="${rowIndex}"]`);
            if (btnConfirmar) {
                btnConfirmar.disabled = true;
                btnConfirmar.title = 'Já confirmado';
                btnConfirmar.classList.remove('btn-primary');
                btnConfirmar.classList.add('btn-success');
                btnConfirmar.textContent = '✓';
            }

        } catch (erro) {
            console.error('Erro ao confirmar agendamento:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        } finally {
            mostrarLoading(false);
        }
    }

    async function gerarSeparacao(rowIndex) {
        const item = state.dados[rowIndex];
        const numPedido = item.num_pedido;

        // 🆕 COLETAR TODOS OS PRODUTOS DO PEDIDO QUE TÊM QTD E DATA PREENCHIDAS
        const produtosDoPedido = [];

        state.dados.forEach((d, idx) => {
            // Filtrar apenas produtos do mesmo pedido (tipo='pedido')
            if (d.tipo === 'pedido' && d.num_pedido === numPedido) {
                // Buscar qtd_editavel e expedicao dos inputs
                const qtdInput = document.getElementById(`qtd-edit-${idx}`);
                const dataExpedicaoInput = document.getElementById(`dt-exped-${idx}`);
                const agendamentoInput = document.getElementById(`dt-agend-${idx}`);
                const protocoloInput = document.getElementById(`protocolo-${idx}`);

                const qtdEditavel = qtdInput ? parseFloat(qtdInput.value || 0) : 0;
                const expedicao = dataExpedicaoInput ? dataExpedicaoInput.value : '';
                const agendamento = agendamentoInput ? agendamentoInput.value : '';
                const protocolo = protocoloInput ? protocoloInput.value.trim() : '';

                // ✅ VERIFICADORES: qtd_editavel > 0 E expedicao preenchida
                if (qtdEditavel > 0 && expedicao) {
                    // Validar se qtd não excede saldo
                    if (qtdEditavel > d.qtd_saldo) {
                        mostrarMensagem('Atenção',
                            `Produto ${d.cod_produto}: Qtd editável (${qtdEditavel}) maior que saldo (${d.qtd_saldo})`,
                            'warning');
                        return;
                    }

                    produtosDoPedido.push({
                        cod_produto: d.cod_produto,
                        quantidade: qtdEditavel,
                        expedicao: expedicao,
                        agendamento: agendamento,
                        protocolo: protocolo
                    });
                }
            }
        });

        // Validação: precisa ter pelo menos 1 produto
        if (produtosDoPedido.length === 0) {
            mostrarMensagem('Atenção',
                'Nenhum produto do pedido tem quantidade e data de expedição preenchidas',
                'warning');
            return;
        }

        // 🆕 VERIFICAR SE O PEDIDO JÁ POSSUI SEPARAÇÕES EXISTENTES
        try {
            mostrarLoading(true);

            const responseVerificar = await fetch('/carteira/simples/api/verificar-separacoes-existentes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: numPedido
                })
            });

            const resultadoVerificar = await responseVerificar.json();

            if (!resultadoVerificar.success) {
                throw new Error(resultadoVerificar.error || 'Erro ao verificar separações');
            }

            mostrarLoading(false);

            // SE TEM SEPARAÇÕES → Abrir modal de escolha
            if (resultadoVerificar.tem_separacoes && resultadoVerificar.lotes.length > 0) {
                console.log(`📦 Pedido ${numPedido} possui ${resultadoVerificar.lotes.length} lote(s) existente(s)`);
                abrirModalEscolhaSeparacao(numPedido, resultadoVerificar.lotes, produtosDoPedido);
                return; // Parar aqui, aguardar escolha do usuário
            }

            // SE NÃO TEM SEPARAÇÕES → Criar nova separação (comportamento original)
            console.log(`✅ Pedido ${numPedido} não possui separações, criando nova...`);
            await criarNovaSeparacao(numPedido, produtosDoPedido);

        } catch (erro) {
            console.error('Erro ao gerar separação:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
            mostrarLoading(false);
        }
    }

    // 🆕 FUNÇÃO PARA CRIAR NOVA SEPARAÇÃO (extraída para reutilização)
    async function criarNovaSeparacao(numPedido, produtosDoPedido) {
        try {
            mostrarLoading(true);

            const response = await fetch('/carteira/simples/api/gerar-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    produtos: produtosDoPedido
                })
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao gerar separação');
            }

            mostrarMensagem('Sucesso',
                `Separação gerada com sucesso!<br>Lote: ${resultado.separacao_lote_id}<br>Produtos: ${resultado.qtd_itens}`,
                'success');

            // Recarregar dados
            carregarDados();

        } catch (erro) {
            console.error('Erro ao criar nova separação:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        } finally {
            mostrarLoading(false);
        }
    }

    // ==============================================
    // MODAL DE ESCOLHA DE SEPARAÇÃO
    // ==============================================

    /**
     * Abre modal para escolher entre criar nova separação ou incluir em existente
     *
     * @param {string} numPedido - Número do pedido
     * @param {Array} lotes - Array de lotes existentes
     * @param {Array} produtosDoPedido - Produtos a serem adicionados
     */
    function abrirModalEscolhaSeparacao(numPedido, lotes, produtosDoPedido) {
        // Preencher número do pedido no título
        document.getElementById('modalPedidoNumero').textContent = numPedido;

        // Renderizar lista de lotes (sem onclick inline)
        const container = document.getElementById('listaSeparacoesExistentes');
        container.innerHTML = lotes.map((lote, index) => `
            <div class="card mb-3 border-primary">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="card-title mb-2">
                                <i class="fas fa-box text-primary me-2"></i>
                                Lote: <strong>${lote.separacao_lote_id}</strong>
                            </h6>
                            <div class="row g-2 small">
                                <div class="col-sm-6">
                                    <i class="fas fa-calendar me-1 text-primary"></i> <span>Expedição:</span> <strong>${lote.expedicao || 'Não informada'}</strong>
                                </div>
                                <div class="col-sm-6">
                                    <i class="fas fa-calendar-check me-1 text-primary"></i> <span>Agendamento:</span> <strong>${lote.agendamento || 'Não informado'}</strong>
                                </div>
                                <div class="col-sm-6">
                                    <i class="fas fa-file-alt me-1 text-primary"></i> <span>Protocolo:</span> <strong>${lote.protocolo || 'Não informado'}</strong>
                                </div>
                                <div class="col-sm-6">
                                    <i class="fas fa-cubes me-1 text-primary"></i> <span>Produtos:</span> <strong>${lote.qtd_itens}</strong>
                                </div>
                                <div class="col-sm-4">
                                    <i class="fas fa-dollar-sign me-1 text-success"></i> <span>Valor:</span> <strong>${formatarMoeda(lote.valor_total)}</strong>
                                </div>
                                <div class="col-sm-4">
                                    <i class="fas fa-pallet me-1 text-warning"></i> <span>Pallets:</span> <strong>${formatarNumero(lote.pallet_total, 2)}</strong>
                                </div>
                                <div class="col-sm-4">
                                    <i class="fas fa-weight me-1 text-info"></i> <span>Peso:</span> <strong>${Math.round(lote.peso_total)} kg</strong>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 d-flex align-items-center">
                            <button type="button" class="btn btn-primary btn-sm w-100 btn-incluir-lote"
                                    data-lote-id="${lote.separacao_lote_id}"
                                    data-lote-index="${index}">
                                <i class="fas fa-plus-circle me-1"></i>
                                Incluir nesta separação
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        // 🔧 CONFIGURAR EVENT LISTENERS para os botões "Incluir nesta separação"
        document.querySelectorAll('.btn-incluir-lote').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const loteId = btn.dataset.loteId;
                console.log(`🔘 Clicou em incluir no lote: ${loteId}`);
                await incluirEmSeparacaoExistente(loteId, numPedido, produtosDoPedido);
            });
        });

        // Configurar botão "Criar nova separação"
        const btnCriarNova = document.getElementById('btnCriarNovaSeparacao');
        btnCriarNova.onclick = async () => {
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalEscolhaSeparacao'));
            modal.hide();

            // Criar nova separação
            await criarNovaSeparacao(numPedido, produtosDoPedido);
        };

        // Abrir modal
        const modalElement = document.getElementById('modalEscolhaSeparacao');
        const modal = new bootstrap.Modal(modalElement);

        // 🆕 LISTENER: Quando o modal for fechado (qualquer forma: X, Cancelar, ESC, backdrop)
        // Garantir que o loading seja fechado se o usuário cancelar
        modalElement.addEventListener('hidden.bs.modal', function handler() {
            console.log('🚪 Modal fechado, garantindo que loading seja fechado');
            mostrarLoading(false);
            // Remover o listener após uso para não acumular
            modalElement.removeEventListener('hidden.bs.modal', handler);
        }, { once: true });

        modal.show();
    }

    /**
     * Inclui produtos em uma separação existente
     *
     * @param {string} separacaoLoteId - ID do lote existente
     * @param {string} numPedido - Número do pedido
     * @param {Array} produtosDoPedido - Produtos a adicionar
     */
    async function incluirEmSeparacaoExistente(separacaoLoteId, numPedido, produtosDoPedido) {
        try {
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalEscolhaSeparacao'));
            modal.hide();

            mostrarLoading(true);

            const response = await fetch('/carteira/simples/api/adicionar-itens-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    separacao_lote_id: separacaoLoteId,
                    num_pedido: numPedido,
                    produtos: produtosDoPedido
                })
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || 'Erro ao adicionar itens à separação');
            }

            // Montar mensagem descritiva
            let mensagem = resultado.message;

            // Adicionar detalhes se houver atualizações
            if (resultado.itens_atualizados && resultado.itens_atualizados.length > 0) {
                mensagem += '<br><br><small class="text-muted">Detalhes das atualizações:</small><br>';
                resultado.itens_atualizados.forEach(item => {
                    mensagem += `<small>• ${item.cod_produto}: ${item.quantidade_anterior} + ${item.quantidade_adicionada} = ${item.quantidade_nova}</small><br>`;
                });
            }

            mostrarMensagem('Sucesso', mensagem, 'success');

            // Recarregar dados
            carregarDados();

        } catch (erro) {
            console.error('Erro ao incluir em separação existente:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        } finally {
            mostrarLoading(false);
        }
    };

    // ==============================================
    // CÁLCULOS DINÂMICOS
    // ==============================================
    function recalcularValoresLinha(rowIndex) {
        const item = state.dados[rowIndex];

        // 🔧 CORREÇÃO: Detectar tipo da linha (pedido ou separação)
        const rowId = item.tipo === 'separacao' ? `row-sep-${rowIndex}` : `row-${rowIndex}`;
        const row = document.getElementById(rowId);

        if (!row) {
            console.warn(`Row não encontrada: ${rowId}`);
            return;
        }

        // 🔧 CORREÇÃO: Usar qtd correta baseada no tipo
        let qtdEditavel;
        if (item.tipo === 'separacao') {
            // Para separações, usar qtd_saldo do item (já atualizado pela API)
            qtdEditavel = parseFloat(item.qtd_saldo) || 0;
        } else {
            // 🔧 CORREÇÃO: Para pedidos, SEMPRE usar qtd_saldo atualizado (não input)
            qtdEditavel = parseFloat(item.qtd_saldo) || 0;
        }

        // Obter dados do row
        const preco = parseFloat(row.dataset.preco) || 0;
        const palletizacao = parseFloat(row.dataset.palletizacao) || 100;
        const pesoBruto = parseFloat(row.dataset.pesoBruto) || 1;

        // Recalcular
        const valorTotal = qtdEditavel * preco;
        const pallets = qtdEditavel / palletizacao;
        const peso = qtdEditavel * pesoBruto;

        // Atualizar células
        const valorTotalEl = row.querySelector('.valor-total');
        const palletsEl = row.querySelector('.pallets');
        const pesoEl = row.querySelector('.peso');

        if (valorTotalEl) valorTotalEl.textContent = formatarMoeda(valorTotal);
        if (palletsEl) palletsEl.textContent = formatarNumero(pallets, 2);
        if (pesoEl) pesoEl.textContent = Math.round(peso);

        // Atualizar também o estado
        item.valor_total = valorTotal;
        item.pallets = pallets;
        item.peso = peso;

        // Estoque é recalculado por recalcularTodasLinhasProduto() chamado no handleTableInput
        // NÃO precisa chamar API legada aqui
    }

    // ==============================================
    // RECÁLCULO DE ESTOQUE COM SAÍDAS ADICIONAIS
    // ==============================================

    /**
     * Recalcula TODAS as linhas de um produto específico.
     * Usado quando qtd ou data editável muda em qualquer linha.
     */
    function recalcularTodasLinhasProduto(codProduto) {
        state.dados.forEach((item, index) => {
            if (item.cod_produto === codProduto) {
                renderizarEstoquePrecalculado(index, item);
            }
        });
    }

    /**
     * 🔧 CORREÇÃO: Coleta TODAS as qtds/datas editáveis preenchidas na tela
     * para um produto específico (PEDIDOS + SEPARAÇÕES).
     * Retorna array de saídas adicionais: [{data, qtd}, ...]
     */
    function coletarSaidasAdicionais(codProduto) {
        const saidasAdicionais = [];

        // Percorrer TODAS as linhas da tabela
        state.dados.forEach((item, index) => {
            // Verificar se é o mesmo produto (considerar códigos unificados)
            if (item.cod_produto !== codProduto) return;

            let qtd = 0;
            let data = null;

            // 🔧 CORREÇÃO: Detectar tipo e buscar inputs corretos
            if (item.tipo === 'separacao') {
                // ✅ IGNORAR separações (já vêm em saidas_previstas do backend)
                return;
            } else {
                // Para pedidos: buscar inputs
                const qtdInput = document.getElementById(`qtd-edit-${index}`);
                const dataInput = document.getElementById(`dt-exped-${index}`);

                if (qtdInput && dataInput) {
                    qtd = parseFloat(qtdInput.value || 0);
                    data = dataInput.value;
                }
            }

            // Se tem qtd E data preenchidas
            if (qtd > 0 && data) {
                saidasAdicionais.push({
                    data: data,
                    qtd: qtd
                });
            }
        });

        return saidasAdicionais;
    }

    /**
     * Recalcula a projeção de estoque considerando saídas adicionais.
     *
     * @param {Array} projecaoBase - Array de projeção do backend (28 dias)
     * @param {Array} saidasAdicionais - Array [{data, qtd}, ...]
     * @param {Number} estoqueAtual - Estoque atual do produto
     * @returns {Object} {projecao: [...], menor_estoque_d7: number}
     */
    function recalcularProjecaoComSaidas(projecaoBase, saidasAdicionais, estoqueAtual = 0) {
        // 🔧 CORREÇÃO: Se projecaoBase está vazia, criar projeção manual
        if (!projecaoBase || projecaoBase.length === 0) {
            // 🔧 CORREÇÃO: Criar projeção manual SEMPRE (mesmo sem saídas adicionais)
            // Isso garante renderização quando backend não envia projecoes_estoque

            // Criar projeção de 28 dias baseada em estoque_atual e saídas adicionais
            const hoje = new Date();
            hoje.setHours(0, 0, 0, 0);

            const projecaoManual = [];
            for (let dia = 0; dia <= 28; dia++) {
                const data = new Date(hoje);
                data.setDate(data.getDate() + dia);
                const dataStr = data.toISOString().split('T')[0];

                projecaoManual.push({
                    dia: dia,
                    data: dataStr,
                    saldo_inicial: dia === 0 ? estoqueAtual : 0,  // D0 = estoque_atual
                    entrada: 0,
                    saida: 0,  // Será preenchido com saidasAdicionais
                    saldo: 0,
                    saldo_final: 0
                });
            }

            projecaoBase = projecaoManual;
        }

        // Criar cópia da projeção base
        const projecaoAjustada = JSON.parse(JSON.stringify(projecaoBase));

        // Agrupar saídas adicionais por data
        const saidasPorData = {};
        saidasAdicionais.forEach(saida => {
            const data = saida.data;
            if (!saidasPorData[data]) {
                saidasPorData[data] = 0;
            }
            saidasPorData[data] += saida.qtd;
        });

        // Ajustar saídas e recalcular saldo_final em cascata
        let menorEstoque = projecaoAjustada[0].saldo_final;

        for (let i = 0; i < projecaoAjustada.length; i++) {
            const proj = projecaoAjustada[i];
            const data = proj.data;

            // Se tem saída adicional nesta data
            if (saidasPorData[data]) {
                proj.saida += saidasPorData[data];
            }

            // Recalcular saldo_final
            if (i === 0) {
                // D0: saldo_final = saldo_inicial - saida + entrada
                proj.saldo_final = proj.saldo_inicial - proj.saida + proj.entrada;
                proj.saldo = proj.saldo_inicial - proj.saida; // saldo sem produção
            } else {
                // D+N: saldo_inicial = saldo_final do dia anterior
                proj.saldo_inicial = projecaoAjustada[i - 1].saldo_final;
                proj.saldo = proj.saldo_inicial - proj.saida; // saldo sem produção
                proj.saldo_final = proj.saldo + proj.entrada;
            }

            // Atualizar menor estoque
            if (proj.saldo_final < menorEstoque) {
                menorEstoque = proj.saldo_final;
            }
        }

        // Calcular menor_estoque_d7
        const menor_estoque_d7 = Math.min(
            ...projecaoAjustada.slice(0, 8).map(p => p.saldo_final)
        );

        return {
            projecao: projecaoAjustada,
            menor_estoque_d7: menor_estoque_d7
        };
    }

    // ==============================================
    // ESTOQUE PROJETADO
    // ==============================================

    /**
     * 🚀 NOVA FUNÇÃO: Renderiza estoque pré-calculado considerando saídas adicionais
     */
    function renderizarEstoquePrecalculado(rowIndex, item) {
        // 🔧 CORREÇÃO: Permitir renderizar mesmo sem projecoes_estoque (usando apenas saídas adicionais)
        const projecoesBase = item.projecoes_estoque || [];

        // 1. Coletar saídas adicionais (qtds/datas editáveis na tela)
        const saidasAdicionais = coletarSaidasAdicionais(item.cod_produto);

        // 2. Recalcular projeção com saídas adicionais
        const estoqueAtual = item.estoque_atual || 0;
        const resultado = recalcularProjecaoComSaidas(projecoesBase, saidasAdicionais, estoqueAtual);

        // 3. Converter formato para exibição
        const projecoesFormatadas = resultado.projecao.map(p => ({
            data: p.data,
            dia_nome: new Date(p.data + 'T00:00:00').toLocaleDateString('pt-BR', { weekday: 'short' }),
            estoque: p.saldo_final || 0,
            saida: p.saida || 0,
            entrada: p.entrada || 0,
            dia: p.dia
        }));

        // 4. Renderizar projeções D0-D28
        renderizarProjecaoDias(rowIndex, projecoesFormatadas);

        // 5. Atualizar EST DATA com base na data de expedição
        atualizarEstoqueNaData(rowIndex, item, projecoesFormatadas);

        // 6. Atualizar MENOR 7D com HIERARQUIA DE CORES
        const menor7dEl = document.getElementById(`menor-7d-${rowIndex}`);
        if (menor7dEl) {
            menor7dEl.textContent = Math.round(resultado.menor_estoque_d7);

            // 🔴 HIERARQUIA DE CORES: Vermelho > Laranja > Verde
            // REGRA 1: NEGATIVO = VERMELHO (PRIORIDADE MÁXIMA)
            if (resultado.menor_estoque_d7 < 0) {
                // 🔧 CORREÇÃO: Usar !important para sobrescrever classes de linha (table-warning, table-info)
                menor7dEl.style.setProperty('background-color', '#dc3545', 'important'); // Vermelho
                menor7dEl.style.setProperty('color', 'white', 'important');
                menor7dEl.style.setProperty('font-weight', 'bold', 'important');
            }
            // REGRA 2: Baixo estoque (< 100) = Amarelo com texto preto
            else if (resultado.menor_estoque_d7 < 100) {
                menor7dEl.style.setProperty('background-color', '#ffc107', 'important');
                menor7dEl.style.setProperty('color', '#000000', 'important');
                menor7dEl.style.setProperty('font-weight', 'bold', 'important');
            }
            // REGRA 3: Estoque OK = Sem cor
            else {
                menor7dEl.style.backgroundColor = '';
                menor7dEl.style.color = '';
                menor7dEl.style.fontWeight = '';
            }
        }
    }

    /**
     * Atualiza o estoque na data de expedição editável
     */
    function atualizarEstoqueNaData(rowIndex, item, projecoes) {
        // 🔧 CORREÇÃO: Buscar input correto baseado no tipo (pedido ou separação)
        const rowId = item.tipo === 'separacao' ? `row-sep-${rowIndex}` : `row-${rowIndex}`;
        const inputData = document.querySelector(`#${rowId} input[type="date"].dt-expedicao`);
        const estDataEl = document.getElementById(`est-data-${rowIndex}`);

        if (!inputData || !estDataEl) return;

        const dataExpedicao = inputData.value;

        if (!dataExpedicao || !projecoes || projecoes.length === 0) {
            estDataEl.textContent = '-';
            return;
        }

        // Calcular quantos dias da data de hoje até a data de expedição
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        const dataExp = new Date(dataExpedicao + 'T00:00:00');
        const diasDiferenca = Math.round((dataExp - hoje) / (1000 * 60 * 60 * 24));

        // Buscar projeção do dia correspondente
        const projecaoDia = projecoes.find(p => p.dia === diasDiferenca);

        if (projecaoDia) {
            // A projeção já vem ajustada com as qtds editáveis
            // NÃO precisa subtrair novamente (evita dupla subtração)
            const estoqueDisponivel = projecaoDia.estoque;

            estDataEl.textContent = Math.round(estoqueDisponivel);

            // 🔴 HIERARQUIA DE CORES: Vermelho > Laranja > Verde
            // REGRA 1: NEGATIVO = VERMELHO (PRIORIDADE MÁXIMA)
            if (estoqueDisponivel < 0) {
                // 🔧 CORREÇÃO: Usar !important para sobrescrever classes de linha (table-warning, table-info)
                estDataEl.style.setProperty('background-color', '#dc3545', 'important'); // Vermelho
                estDataEl.style.setProperty('color', 'white', 'important');
                estDataEl.style.setProperty('font-weight', 'bold', 'important');
            }
            // REGRA 2: Baixo estoque (< 100) = Amarelo com texto preto
            else if (estoqueDisponivel < 100) {
                estDataEl.style.setProperty('background-color', '#ffc107', 'important');
                estDataEl.style.setProperty('color', '#000000', 'important');
                estDataEl.style.setProperty('font-weight', 'bold', 'important');
            }
            // REGRA 3: Estoque OK = Sem cor
            else {
                estDataEl.style.backgroundColor = '';
                estDataEl.style.color = '';
                estDataEl.style.fontWeight = '';
            }
        } else {
            estDataEl.textContent = '-';
        }
    }

    /**
     * ⚠️ FUNÇÕES LEGADAS REMOVIDAS:
     * - carregarEstoqueProjetado() - substituída por renderizarEstoquePrecalculado()
     * - atualizarEstoqueLinha() - não mais necessária
     * Agora tudo usa dados pré-calculados do backend com ajustes no frontend
     */

    function renderizarProjecaoDias(rowIndex, projecoes) {
        if (!projecoes || projecoes.length === 0) return;

        const container = document.getElementById(`projecao-dias-${rowIndex}`);

        // ✅ MOSTRAR TODOS OS 28 DIAS (sem offset - sem navegação)
        const diasVisiveis = projecoes.slice(0, 28);

        const html = diasVisiveis.map(dia => {
            let classe = 'estoque-dia';
            if (dia.estoque < 0) classe += ' negativo';
            else if (dia.estoque < 100) classe += ' baixo';

            // 🔧 4. REMOVER DATAS - Apenas mostrar número do estoque
            // Tooltip mantém a data completa para referência
            const dataFormatada = new Date(dia.data + 'T00:00:00').toLocaleDateString('pt-BR');
            const diaIndice = dia.dia !== undefined ? `D${dia.dia}` : '';

            return `
                <span class="${classe}" title="${diaIndice} - ${dataFormatada}">
                    ${formatarNumero(dia.estoque, 0)}
                </span>
            `;
        }).join('');

        container.innerHTML = html;
    }

    // 🆕 NAVEGAÇÃO GLOBAL DE ESTOQUE
    function navegarEstoque(_rowIndex, direcao) {
        // Atualizar offset GLOBAL
        const novoOffset = Math.max(0, Math.min(21, state.projecaoEstoqueOffset + direcao)); // Máximo 21 (28-7)
        state.projecaoEstoqueOffset = novoOffset;

        // ✅ ATUALIZAR CABEÇALHO DE DATAS
        atualizarCabecalhoEstoque();

        // 🆕 RENDERIZAR TODAS AS LINHAS (não só a clicada)
        state.dados.forEach((item, index) => {
            if (item.projecoes_estoque && item.projecoes_estoque.length > 0) {
                // Recalcular com saídas adicionais
                const saidasAdicionais = coletarSaidasAdicionais(item.cod_produto);
                const estoqueAtual = item.estoque_atual || 0;
                const resultado = recalcularProjecaoComSaidas(item.projecoes_estoque, saidasAdicionais, estoqueAtual);

                const projecoesFormatadas = resultado.projecao.map(p => ({
                    data: p.data,
                    dia_nome: new Date(p.data + 'T00:00:00').toLocaleDateString('pt-BR', { weekday: 'short' }),
                    estoque: p.saldo_final || 0,
                    saida: p.saida || 0,
                    entrada: p.entrada || 0,
                    dia: p.dia
                }));

                renderizarProjecaoDias(index, projecoesFormatadas);
            }
        });

        console.log(`📊 Offset global atualizado para: ${novoOffset} (mostrando D${novoOffset} a D${novoOffset + 6})`);
    }

    // ==============================================
    // UTILITÁRIOS
    // ==============================================
    function formatarData(dataStr) {
        if (!dataStr) return '';
        const data = new Date(dataStr + 'T00:00:00');
        return data.toLocaleDateString('pt-BR');
    }

    function formatarNumero(numero, decimais = 2) {
        if (numero === null || numero === undefined) return '-';
        return parseFloat(numero).toLocaleString('pt-BR', {
            minimumFractionDigits: decimais,
            maximumFractionDigits: decimais
        });
    }

    function formatarMoeda(valor) {
        if (valor === null || valor === undefined) return 'R$ 0';
        return 'R$ ' + Math.round(valor).toLocaleString('pt-BR');
    }

    function truncarTexto(texto, tamanho) {
        if (!texto || texto.length <= tamanho) return texto;
        return texto.substring(0, tamanho) + '...';
    }

    function inicializarTooltips() {
        const tooltips = document.querySelectorAll('.truncate-tooltip');
        tooltips.forEach(el => {
            el.title = el.title || el.textContent;
        });
    }

    // ==============================================
    // CONTADORES E PAGINAÇÃO
    // ==============================================

    // ==============================================
    // MODAIS
    // ==============================================
    function mostrarLoading(mostrar) {
        console.log(`🔄 mostrarLoading(${mostrar})`);

        const modal = document.getElementById('modalLoading');
        if (!modal) {
            console.error('❌ Modal de loading não encontrado!');
            return;
        }

        try {
            // Criar instância única na primeira vez
            if (!state.modalLoading) {
                state.modalLoading = new bootstrap.Modal(modal, {
                    backdrop: false, // Sem backdrop para evitar conflitos
                    keyboard: false  // Não fecha com ESC
                });
            }

            if (mostrar) {
                console.log('⏳ Abrindo modal...');
                state.modalLoading.show();
            } else {
                console.log('✅ Fechando modal...');
                // Usar setTimeout para garantir que fecha após renderização
                setTimeout(() => {
                    state.modalLoading.hide();
                }, 100);
            }
        } catch (erro) {
            console.error('❌ Erro ao controlar modal:', erro);
        }
    }

    function mostrarMensagem(titulo, mensagem, tipo = 'info') {
        const modal = document.getElementById('modalMensagem');
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);

        document.getElementById('modalMensagemTitulo').textContent = titulo;
        document.getElementById('modalMensagemConteudo').innerHTML = mensagem;

        // Aplicar cor do header
        const header = modal.querySelector('.modal-header');
        header.className = `modal-header bg-${tipo} text-white`;

        bsModal.show();
    }

})();
