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
        saidasNaoVisiveis: {}, // 🆕 Saídas de pedidos NÃO visíveis {cod_produto: [{data, qtd}]}
        mapaUnificacao: {}, // 🆕 Mapa de códigos unificados {cod_produto: [cod1, cod2, cod3]}

        // 🚀 ÍNDICES DE LOOKUP (otimização: O(n) → O(k))
        indices: {
            porProduto: new Map(),  // cod_produto -> [índices no state.dados]
        },

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

        // 🆕 Event listener para botão de ocultar painel flutuante
        const btnOcultarPainel = document.getElementById('btn-ocultar-painel');
        if (btnOcultarPainel) {
            btnOcultarPainel.addEventListener('click', function() {
                const painel = document.getElementById('painel-resumo-separacao');
                if (painel) {
                    painel.style.display = 'none';
                }
            });
        }

        // 🆕 FUNCIONALIDADE 3: Checkboxes Sep./Pdd.
        const checkboxSep = document.getElementById('filtro-tipo-sep');
        const checkboxPdd = document.getElementById('filtro-tipo-pdd');

        if (checkboxSep) {
            checkboxSep.addEventListener('change', aplicarFiltroTipo);
        }

        if (checkboxPdd) {
            checkboxPdd.addEventListener('change', aplicarFiltroTipo);
        }
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
            state.saidasNaoVisiveis = resultado.saidas_nao_visiveis || {};  // 🆕 Capturar saídas não visíveis
            state.mapaUnificacao = resultado.mapa_unificacao || {};  // 🆕 Capturar mapa de códigos unificados

            console.log(`✅ Dados carregados: ${state.dados.length} linhas visíveis`);
            console.log(`✅ Saídas não visíveis: ${Object.keys(state.saidasNaoVisiveis).length} produtos`);
            console.log(`✅ Mapa de unificação: ${Object.keys(state.mapaUnificacao).length} produtos com códigos unificados`);

            // 🚀 CRÍTICO: Construir índices ANTES de renderizar (coletarTodasSaidas depende deles)
            construirIndices();
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

    // ==============================================
    // 🚀 ÍNDICES DE LOOKUP (OTIMIZAÇÃO)
    // ==============================================

    /**
     * Constrói índices de lookup para acesso O(1) por cod_produto.
     * DEVE ser chamado após carregarDados() e sempre que state.dados mudar.
     *
     * SEGURANÇA: Apenas mapeia posições, NÃO cacheia dados.
     */
    function construirIndices() {
        console.time('⏱️ construirIndices');

        // Limpar índices anteriores
        state.indices.porProduto.clear();

        // Construir índice por produto
        state.dados.forEach((item, index) => {
            const cod = item.cod_produto;
            if (!state.indices.porProduto.has(cod)) {
                state.indices.porProduto.set(cod, []);
            }
            state.indices.porProduto.get(cod).push(index);
        });

        console.timeEnd('⏱️ construirIndices');
        console.log(`📊 Índices construídos: ${state.indices.porProduto.size} produtos únicos`);
    }

    // ==============================================
    // 🚀 DEBOUNCE AGRUPADO POR PRODUTO (OTIMIZAÇÃO)
    // ==============================================

    /**
     * Gerenciador de debounce para recálculos.
     * Agrupa múltiplas edições rápidas em uma única atualização.
     *
     * SEGURANÇA: Dados são lidos FRESCOS do DOM quando o timer dispara.
     */
    const recalculoPendente = {
        produtos: new Set(),
        timer: null,
        DELAY: 150  // ms - curto o suficiente para parecer instantâneo
    };

    /**
     * Agenda recálculo de um produto (debounce agrupado).
     * Múltiplas chamadas dentro de 150ms são agrupadas.
     *
     * @param {string} codProduto - Código do produto a recalcular
     */
    function agendarRecalculoProduto(codProduto) {
        recalculoPendente.produtos.add(codProduto);

        if (recalculoPendente.timer) {
            clearTimeout(recalculoPendente.timer);
        }

        recalculoPendente.timer = setTimeout(() => {
            // 🚀 requestAnimationFrame: Agrupar todas atualizações DOM em um único frame
            requestAnimationFrame(() => {
                // Executar recálculo com dados FRESCOS do DOM
                recalculoPendente.produtos.forEach(cod => {
                    recalcularTodasLinhasProduto(cod);
                });
                recalculoPendente.produtos.clear();

                // Atualizar resumo apenas UMA vez ao final
                atualizarResumoSeparacao();
            });
        }, recalculoPendente.DELAY);
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

        // Aplicar classes visuais
        aplicarClassesVisuais();
        // 🆕 Inicializar tooltips e popovers para observações e tags
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

        // ✅ CORREÇÃO: Aplicar visibilidade nas novas linhas carregadas
        // Verificar e ocultar pedidos com saldo=0 no novo lote
        let pedidosOcultadosNovos = 0;
        for (let i = currentRendered; i < nextBatch; i++) {
            const item = state.dados[i];
            if (item.tipo === 'pedido') {
                const saldoAtual = parseFloat(item.qtd_saldo) || 0;

                if (saldoAtual === 0) {
                    const row = document.getElementById(`row-${i}`);
                    if (row) {
                        row.style.display = 'none';
                        pedidosOcultadosNovos++;
                    }
                }
            }
        }

        if (pedidosOcultadosNovos > 0) {
            console.log(`👻 ${pedidosOcultadosNovos} novo(s) pedido(s) com saldo=0 ocultado(s) no virtual scrolling`);
        }

        console.log(`✅ ${nextBatch} de ${state.dados.length} linhas renderizadas`);
    }

    // 🆕 FUNÇÃO PARA APLICAR CLASSES VISUAIS (bordas - cor já aplicada na renderização)
    // 🚀 OTIMIZADO: Itera apenas range visível (não mais 2000+ items)
    function aplicarClassesVisuais() {
        let pedidoAnterior = null;
        let loteAnterior = null;

        // 🚀 Limitar ao range renderizado + buffer de segurança
        const endIndex = Math.min(state.virtualScroll.lastVisibleIndex + 50, state.dados.length);

        for (let index = 0; index < endIndex; index++) {
            const item = state.dados[index];
            const row = document.getElementById(item.tipo === 'separacao' ? `row-sep-${index}` : `row-${index}`);
            if (!row) continue; // Skip se não renderizado

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
        }
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
                data-separacao-lote-id="${item.separacao_lote_id || ''}"
                data-num-pedido="${item.num_pedido}"
                data-cod-produto="${item.cod_produto}"
                data-palletizacao="${item.palletizacao}"
                data-peso-bruto="${item.peso_bruto}"
                data-preco="${item.preco_produto_pedido}"
                data-qtd-saldo="${item.qtd_saldo}">

                <!-- Dados básicos -->
                <td>
                    <span class="num-pedido-standby" data-num-pedido="${item.num_pedido}"
                          style="cursor: pointer; text-decoration: underline;"
                          title="Clique para enviar para standby">
                        ${item.num_pedido}
                    </span>
                </td>
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
                <td>
                    <span class="cod-produto-clicavel" data-cod-produto="${item.cod_produto}"
                          style="cursor: pointer;">
                        ${item.cod_produto}
                    </span>
                </td>
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
                    <button type="button" class="btn btn-info btn-sm-custom btn-d1-all"
                        data-row-index="${index}" title="Adicionar +1 dia útil em todo o pedido">
                        D1»
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
                        data-row-index="${index}"
                        value="${item.agendamento || ''}">
                </td>

                <!-- Botão totais do protocolo -->
                <td class="text-center">
                    <button type="button" class="btn btn-info btn-sm-custom btn-totais-protocolo"
                        data-row-index="${index}"
                        data-protocolo="${item.protocolo || ''}"
                        title="Ver totais do protocolo">
                        📊
                    </button>
                </td>

                <td>
                    <input type="text" class="form-control form-control-sm protocolo"
                        data-row-index="${index}"
                        id="${protocoloId}"
                        maxlength="50"
                        value="${item.protocolo || ''}">
                </td>

                <!-- Botão confirmar agendamento -->
                <td class="text-center">
                    <button type="button" class="btn ${item.agendamento_confirmado ? 'btn-success' : 'btn-primary'} btn-sm-custom btn-confirmar"
                        data-row-index="${index}"
                        title="${item.agendamento_confirmado ? 'Clique para desconfirmar' : 'Confirmar agendamento'}">
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

        // 🆕 Montar ícones indicadores de observação e tags
        const iconeObservacao = item.observ_ped_1
            ? `<span class="icone-info icone-obs" title="${escapeHtml(item.observ_ped_1)}" data-bs-toggle="tooltip" data-bs-placement="top">📝</span>`
            : '';
        const iconeTags = montarIconeTags(item.tags_pedido);

        return `
            <tr id="${rowId}"
                data-tipo="pedido"
                data-num-pedido="${item.num_pedido}"
                data-cod-produto="${item.cod_produto}"
                data-palletizacao="${item.palletizacao}"
                data-peso-bruto="${item.peso_bruto}"
                data-preco="${item.preco_produto_pedido}"
                data-qtd-saldo="${item.qtd_saldo}">

                <!-- Dados básicos -->
                <td>
                    <span class="num-pedido-standby" data-num-pedido="${item.num_pedido}"
                          style="cursor: pointer; text-decoration: underline;"
                          title="Clique para enviar para standby">
                        ${item.num_pedido}
                    </span>
                </td>
                <td>${item.pedido_cliente || ''}</td>
                <td>${item.data_pedido ? new Date(item.data_pedido + 'T00:00:00').toLocaleDateString('pt-BR') : ''}</td>
                <td>${item.data_entrega_pedido ? new Date(item.data_entrega_pedido + 'T00:00:00').toLocaleDateString('pt-BR') : ''}</td>
                <td>${item.cnpj_cpf}</td>
                <td>
                    <div class="d-flex align-items-center gap-1">
                        <span class="truncate-tooltip" title="${item.raz_social_red || ''}">
                            ${razaoSocialTrunc}
                        </span>
                        ${iconeObservacao}${iconeTags}
                    </div>
                </td>
                <td>${item.estado || ''}</td>
                <td>
                    <span class="truncate-tooltip" title="${item.municipio || ''}">
                        ${municipioTrunc}
                    </span>
                </td>
                <td>
                    <span class="cod-produto-clicavel" data-cod-produto="${item.cod_produto}"
                          style="cursor: pointer;">
                        ${item.cod_produto}
                    </span>
                </td>
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
                    <button type="button" class="btn btn-info btn-sm-custom btn-d1-all"
                        data-row-index="${index}" title="Adicionar +1 dia útil em todo o pedido">
                        D1»
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
                        data-row-index="${index}"
                        value="${item.agendamento || ''}">
                </td>

                <!-- Botão totais do protocolo -->
                <td class="text-center">
                    <button type="button" class="btn btn-info btn-sm-custom btn-totais-protocolo"
                        data-row-index="${index}"
                        data-protocolo="${item.protocolo || ''}"
                        title="Ver totais do protocolo">
                        📊
                    </button>
                </td>

                <td>
                    <input type="text" class="form-control form-control-sm protocolo"
                        data-row-index="${index}"
                        id="${protocoloId}"
                        maxlength="50"
                        value="${item.protocolo || ''}">
                </td>

                <!-- Botão confirmar agendamento -->
                <td class="text-center">
                    <button type="button" class="btn ${item.agendamento_confirmado ? 'btn-success' : 'btn-primary'} btn-sm-custom btn-confirmar"
                        data-row-index="${index}"
                        title="${item.agendamento_confirmado ? 'Clique para desconfirmar' : 'Confirmar agendamento'}">
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
    // 🆕 CÁLCULO EM TEMPO REAL - RESUMO DA SEPARAÇÃO
    // ==============================================

    /**
     * Calcula totais (Valor, Peso, Pallet) de TODOS os itens que têm:
     * - QTD EDIT > 0
     * - DT EXPED preenchida
     *
     * Agrupa por num_pedido para exibir múltiplos pedidos separadamente
     */
    function calcularTotaisSeparacao() {
        const totaisPorPedido = {};

        state.dados.forEach((item, index) => {
            // Processar APENAS linhas de pedido (tipo='pedido')
            if (item.tipo !== 'pedido') return;

            const numPedido = item.num_pedido;
            const qtdInput = document.getElementById(`qtd-edit-${index}`);
            const dataExpedicaoInput = document.getElementById(`dt-exped-${index}`);

            const qtdEditavel = qtdInput ? parseFloat(qtdInput.value || 0) : 0;
            const dataExpedicao = dataExpedicaoInput ? dataExpedicaoInput.value : '';

            // Critério: QTD > 0 E DATA preenchida
            if (qtdEditavel > 0 && dataExpedicao) {
                // Inicializar totais do pedido se ainda não existe
                if (!totaisPorPedido[numPedido]) {
                    totaisPorPedido[numPedido] = {
                        numPedido: numPedido,
                        razaoSocial: item.raz_social_red || '',
                        qtdItens: 0,
                        valorTotal: 0,
                        pesoTotal: 0,
                        palletTotal: 0
                    };
                }

                // Calcular valores do item
                const preco = parseFloat(item.preco_produto_pedido) || 0;
                const pesoBruto = parseFloat(item.peso_bruto) || 0;
                const palletizacao = parseFloat(item.palletizacao) || 100;

                const valorItem = qtdEditavel * preco;
                const pesoItem = qtdEditavel * pesoBruto;
                const palletItem = palletizacao > 0 ? qtdEditavel / palletizacao : 0;

                // Acumular totais
                totaisPorPedido[numPedido].qtdItens += 1;
                totaisPorPedido[numPedido].valorTotal += valorItem;
                totaisPorPedido[numPedido].pesoTotal += pesoItem;
                totaisPorPedido[numPedido].palletTotal += palletItem;
            }
        });

        return totaisPorPedido;
    }

    /**
     * Atualiza o Painel Flutuante com os totais em tempo real
     */
    function atualizarPainelFlutuante() {
        try {
            const totaisPorPedido = calcularTotaisSeparacao();
            const pedidos = Object.values(totaisPorPedido);

            // Calcular totais gerais (soma de todos os pedidos)
            const totaisGerais = pedidos.reduce((acc, p) => {
                acc.qtdItens += p.qtdItens;
                acc.valorTotal += p.valorTotal;
                acc.pesoTotal += p.pesoTotal;
                acc.palletTotal += p.palletTotal;
                return acc;
            }, { qtdItens: 0, valorTotal: 0, pesoTotal: 0, palletTotal: 0 });

            // Elementos do painel
            const painel = document.getElementById('painel-resumo-separacao');
            const conteudo = document.getElementById('painel-resumo-conteudo');

            // ✅ PROTEÇÃO: Se elementos não existem, sair silenciosamente
            if (!painel || !conteudo) {
                console.warn('⚠️ Elementos do painel flutuante não encontrados no DOM');
                return;
            }

            // Se não há itens selecionados, ocultar painel
            if (totaisGerais.qtdItens === 0) {
                painel.style.display = 'none';
                return;
            }

            // Exibir painel
            painel.style.display = 'block';

        // Renderizar conteúdo
        let html = '';

        // Se houver múltiplos pedidos, mostrar separado
        if (pedidos.length > 1) {
            html += '<div class="mb-2"><strong>📦 Por Pedido:</strong></div>';
            pedidos.forEach(p => {
                html += `
                    <div class="card mb-2" style="font-size: 10px;">
                        <div class="card-body p-2">
                            <div><strong>${p.numPedido}</strong></div>
                            <div class="text-muted" style="font-size: 9px;">${p.razaoSocial.substring(0, 25)}</div>
                            <div class="mt-1">
                                <div>${p.qtdItens} itens</div>
                                <div>R$ ${p.valorTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                                <div>${p.pesoTotal.toFixed(0)} kg</div>
                                <div>${p.palletTotal.toFixed(2)} PLT</div>
                            </div>
                        </div>
                    </div>
                `;
            });

            html += '<hr class="my-2">';
        }

        // Totais gerais
        html += `
            <div><strong>📊 TOTAL GERAL</strong></div>
            <div class="mt-2">
                <div class="d-flex justify-content-between">
                    <span>Produtos:</span>
                    <strong>${totaisGerais.qtdItens} itens</strong>
                </div>
                <div class="d-flex justify-content-between text-success">
                    <span>Valor:</span>
                    <strong>R$ ${totaisGerais.valorTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong>
                </div>
                <div class="d-flex justify-content-between text-info">
                    <span>Peso:</span>
                    <strong>${totaisGerais.pesoTotal.toFixed(0)} kg</strong>
                </div>
                <div class="d-flex justify-content-between text-warning">
                    <span>Pallet:</span>
                    <strong>${totaisGerais.palletTotal.toFixed(2)} PLT</strong>
                </div>
            </div>
        `;

            conteudo.innerHTML = html;

        } catch (erro) {
            console.error('Erro ao atualizar painel flutuante:', erro);
        }
    }

    /**
     * Atualiza Painel Flutuante com totais em tempo real
     * Chamado sempre que QTD EDIT ou DT EXPED mudam
     */
    function atualizarResumoSeparacao() {
        atualizarPainelFlutuante();
        // ❌ REMOVIDO: atualizarLinhasTotaisPedidos() - interferia na renderização
    }

    // ==============================================
    // HANDLERS DE EVENTOS
    // ==============================================
    function handleTableClick(e) {
        const target = e.target;

        // 🆕 FUNCIONALIDADE 2: Clique em código de produto → Rastrear produto (PRIORIDADE MÁXIMA)
        if (target.classList.contains('cod-produto-clicavel')) {
            const codProduto = target.dataset.codProduto;
            if (codProduto) {
                rastrearProduto(codProduto);
                return;
            }
        }

        // 🆕 FUNCIONALIDADE 3: Clique em número do pedido → Enviar para standby
        if (target.classList.contains('num-pedido-standby')) {
            const numPedido = target.dataset.numPedido;
            if (numPedido) {
                abrirModalStandby(numPedido);
                return;
            }
        }

        // 🆕 FUNCIONALIDADE 1: Clique em linha de separação → Exibir toast de totais
        // APENAS se NÃO clicou em input, button, a OU código do produto
        if (target.closest('tr')?.dataset.tipo === 'separacao' &&
            !target.closest('input, button, a') &&
            !target.classList.contains('cod-produto-clicavel')) {
            const row = target.closest('tr');
            const separacaoLoteId = row.dataset.separacaoLoteId;
            if (separacaoLoteId) {
                mostrarToastTotaisSeparacao(separacaoLoteId);
                return;
            }
        }

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

        // Botão D1» (D1 para todo o pedido)
        else if (target.classList.contains('btn-d1-all')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            adicionarDiaUtilTodos(rowIndex);
        }

        // Botão confirmar
        else if (target.classList.contains('btn-confirmar')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            confirmarAgendamento(rowIndex);
        }

        // Botão totais do protocolo
        else if (target.classList.contains('btn-totais-protocolo')) {
            const protocolo = target.dataset.protocolo;
            mostrarTotaisProtocolo(protocolo);
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

            // ✅ CORREÇÃO: Apenas separações devem atualizar backend
            const isSeparacao = item.tipo === 'separacao';
            const separacaoLoteId = item.separacao_lote_id;

            // Se mudou data de uma separação com lote, atualizar todo o lote NO BACKEND
            if (isSeparacao && separacaoLoteId) {
                await atualizarCampoSeparacaoLote(separacaoLoteId, 'expedicao', novoValor);
            }
            // ✅ REMOVIDO: Não atualizar CarteiraPrincipal - edição é apenas local até clicar "OK"
            // Quando clicar "OK", a data será copiada para a Separacao criada

            // 🚀 OTIMIZADO: Usar debounce agrupado (150ms)
            agendarRecalculoProduto(item.cod_produto);
        }

        // ✅ NOVO: Mudança na data de agendamento
        if (target.classList.contains('dt-agendamento')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const item = state.dados[rowIndex];
            const novoValor = target.value;

            // Apenas separações devem atualizar backend
            const isSeparacao = item.tipo === 'separacao';
            const separacaoLoteId = item.separacao_lote_id;

            if (isSeparacao && separacaoLoteId) {
                await atualizarCampoSeparacaoLote(separacaoLoteId, 'agendamento', novoValor);
            }
        }
    }

    function handleTableInput(e) {
        const target = e.target;

        // Mudança na quantidade editável de PEDIDO
        if (target.classList.contains('qtd-editavel')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const item = state.dados[rowIndex];

            // 🔧 CORREÇÃO: Sincronizar valor do DOM para state.dados
            item.qtd_editavel = parseFloat(target.value || 0);

            // Recalcular valores da linha (valor total, pallets, peso) - IMEDIATO
            recalcularValoresLinha(rowIndex);

            // 🚀 OTIMIZADO: Usar debounce agrupado (150ms)
            agendarRecalculoProduto(item.cod_produto);
        }

        // 🔧 CORREÇÃO: Mudança na data de expedição de PEDIDO
        if (target.id && target.id.startsWith('dt-exped-') && !target.id.startsWith('dt-exped-sep-')) {
            const rowIndex = parseInt(target.id.replace('dt-exped-', ''));
            if (state.dados[rowIndex] && state.dados[rowIndex].tipo === 'pedido') {
                state.dados[rowIndex].expedicao_editavel = target.value;
            }
        }

        // 🔧 CORREÇÃO: Mudança na data de agendamento de PEDIDO
        if (target.id && target.id.startsWith('dt-agend-') && !target.id.startsWith('dt-agend-sep-')) {
            const rowIndex = parseInt(target.id.replace('dt-agend-', ''));
            if (state.dados[rowIndex] && state.dados[rowIndex].tipo === 'pedido') {
                state.dados[rowIndex].agendamento_editavel = target.value;
            }
        }

        // 🔧 CORREÇÃO: Mudança no protocolo de PEDIDO
        if (target.id && target.id.startsWith('protocolo-') && !target.id.startsWith('protocolo-sep-')) {
            const rowIndex = parseInt(target.id.replace('protocolo-', ''));
            if (state.dados[rowIndex] && state.dados[rowIndex].tipo === 'pedido') {
                state.dados[rowIndex].protocolo_editavel = target.value.trim();
            }
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

        // ✅ NOVO: Mudança no protocolo de SEPARAÇÃO
        if (target.classList.contains('protocolo')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const item = state.dados[rowIndex];
            const novoValor = target.value.trim();

            // Apenas separações devem atualizar backend
            const isSeparacao = item.tipo === 'separacao';
            const separacaoLoteId = item.separacao_lote_id;

            if (isSeparacao && separacaoLoteId) {
                // Debounce para evitar múltiplas chamadas
                clearTimeout(target.debounceTimer);
                target.debounceTimer = setTimeout(() => {
                    atualizarCampoSeparacaoLote(separacaoLoteId, 'protocolo', novoValor);
                }, 800); // 800ms de delay (maior que qtd porque é texto)
            }
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

                // ✅ RECALCULAR ESTOQUES localmente (SEM backend)
                recalcularTodasLinhasProduto(item.cod_produto);

                console.log(`✅ Separação deletada e estoques recalculados (sem reload)`);
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

            // ✅ RECALCULAR ESTOQUES localmente (SEM backend)
            recalcularTodasLinhasProduto(item.cod_produto);

            console.log(`✅ Quantidade da separação ${separacaoId} atualizada para ${novaQtd} (sem reload)`);

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

        // ✅ CORREÇÃO: Atualizar painel flutuante
        atualizarResumoSeparacao();
    }

    function adicionarTodosProdutos(rowIndex) {
        const item = state.dados[rowIndex];
        const numPedido = item.num_pedido;

        // Coletar todos os produtos únicos afetados
        const produtosAfetados = new Set();

        // Encontrar todos os produtos do mesmo pedido
        // 🔧 CORREÇÃO: Filtrar apenas tipo='pedido' e armazenar no state.dados
        state.dados.forEach((d, idx) => {
            if (d.tipo === 'pedido' && d.num_pedido === numPedido) {
                // 🔧 CORREÇÃO: Armazenar no state.dados (funciona mesmo sem DOM renderizado)
                d.qtd_editavel = d.qtd_saldo;

                // Tentar atualizar DOM se existir (para UI)
                const inputQtd = document.getElementById(`qtd-edit-${idx}`);
                if (inputQtd) {
                    inputQtd.value = d.qtd_saldo;
                    recalcularValoresLinha(idx);
                }
                produtosAfetados.add(d.cod_produto);
            }
        });

        // Recalcular estoques para cada produto afetado
        produtosAfetados.forEach(codProduto => {
            recalcularTodasLinhasProduto(codProduto);
        });

        // ✅ CORREÇÃO: Atualizar painel flutuante
        atualizarResumoSeparacao();

        // ✅ Removido toast de confirmação para agilizar fluxo
        // mostrarMensagem('Sucesso', `Todas as quantidades do pedido ${numPedido} foram adicionadas`, 'success');
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

        // Se for separação, atualizar TODOS os produtos do mesmo lote NO BACKEND
        if (item.tipo === 'separacao' && item.separacao_lote_id) {
            await atualizarCampoSeparacaoLote(item.separacao_lote_id, 'expedicao', novaData);
        }
        // ✅ REMOVIDO: Não atualizar CarteiraPrincipal quando tipo === 'pedido'
        // A data editada será usada apenas ao clicar "OK" para gerar separação

        // Recalcular TODAS as linhas do mesmo produto (atualiza UI)
        recalcularTodasLinhasProduto(item.cod_produto);
    }

    // ✅ FUNÇÃO PARA ADICIONAR D+1 EM TODAS AS LINHAS DO PEDIDO (D1»)
    async function adicionarDiaUtilTodos(rowIndex) {
        const item = state.dados[rowIndex];
        const numPedido = item.num_pedido;

        // Coletar todos os produtos únicos afetados
        const produtosAfetados = new Set();

        // Calcular a nova data (D+1) baseada na data atual ou hoje
        const inputIdBase = item.tipo === 'separacao' ? `dt-exped-sep-${rowIndex}` : `dt-exped-${rowIndex}`;
        const inputDataBase = document.getElementById(inputIdBase);
        const dataAtual = inputDataBase && inputDataBase.value ? new Date(inputDataBase.value + 'T00:00:00') : new Date();

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

        // Encontrar todos os itens do mesmo pedido e aplicar a data
        // ✅ CORREÇÃO: Pular itens que já estão em separação (têm separacao_lote_id)
        // Separações já têm controle de datas próprio via separacao_lote_id
        // 🔧 CORREÇÃO: Filtrar apenas tipo='pedido' e armazenar no state.dados
        for (const [idx, d] of state.dados.entries()) {
            if (d.tipo === 'pedido' && d.num_pedido === numPedido && !d.separacao_lote_id) {
                // 🔧 CORREÇÃO: Armazenar no state.dados (funciona mesmo sem DOM renderizado)
                d.expedicao_editavel = novaData;

                // Tentar atualizar DOM se existir (para UI)
                const inputId = `dt-exped-${idx}`;
                const inputData = document.getElementById(inputId);
                if (inputData) {
                    inputData.value = novaData;
                }
                produtosAfetados.add(d.cod_produto);
            }
        }

        // Recalcular estoques para cada produto afetado
        produtosAfetados.forEach(codProduto => {
            recalcularTodasLinhasProduto(codProduto);
        });
    }

    // ✅ FUNÇÃO GENÉRICA PARA ATUALIZAR QUALQUER CAMPO DE UM LOTE DE SEPARAÇÃO
    async function atualizarCampoSeparacaoLote(separacaoLoteId, campo, valor) {
        try {
            // Preparar payload baseado no campo
            const payload = {
                separacao_lote_id: separacaoLoteId
            };
            payload[campo] = valor;

            // CHAMAR BACKEND PARA ATUALIZAR BANCO DE DADOS
            const response = await fetch('/carteira/simples/api/atualizar-separacao-lote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const resultado = await response.json();

            if (!resultado.success) {
                throw new Error(resultado.error || `Erro ao atualizar ${campo} do lote`);
            }

            console.log(`✅ Backend: ${resultado.message}`);

            // 🔄 ATUALIZAR FRONTEND (UI e estado local)
            const produtosAfetados = new Set();

            state.dados.forEach((d, idx) => {
                if (d.tipo === 'separacao' && d.separacao_lote_id === separacaoLoteId) {
                    // Atualizar input no DOM baseado no campo
                    let inputId = '';
                    if (campo === 'expedicao') {
                        inputId = `dt-exped-sep-${idx}`;
                    } else if (campo === 'agendamento') {
                        inputId = `dt-agend-sep-${idx}`;
                    } else if (campo === 'protocolo') {
                        inputId = `protocolo-sep-${idx}`;
                    }

                    const input = document.getElementById(inputId);
                    if (input) {
                        input.value = valor;
                    }

                    // Atualizar estado local
                    d[campo] = valor;

                    // Atualizar estoque se veio do backend (apenas para datas)
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

    async function confirmarAgendamento(rowIndex) {
        const item = state.dados[rowIndex];

        // ✅ ALTERNAR estado atual (True <-> False)
        const estadoAtual = item.agendamento_confirmado || false;
        const novoEstado = !estadoAtual;

        // Se está confirmando (False -> True), protocolo é obrigatório
        if (novoEstado && !item.protocolo) {
            const protocoloInput = document.getElementById(`protocolo-${rowIndex}`) ||
                                   document.getElementById(`protocolo-sep-${rowIndex}`);
            const protocolo = protocoloInput ? protocoloInput.value.trim() : '';

            if (!protocolo) {
                mostrarMensagem('Atenção', 'Protocolo é obrigatório para confirmação', 'warning');
                return;
            }
        }

        try {
            // ✅ CORREÇÃO: Apenas separações devem atualizar backend
            const isSeparacao = item.tipo === 'separacao';
            const separacaoLoteId = item.separacao_lote_id;

            if (isSeparacao && separacaoLoteId) {
                // Atualizar via API de lote
                await atualizarCampoSeparacaoLote(separacaoLoteId, 'agendamento_confirmado', novoEstado);
            }

            // ✅ ATUALIZAR TODAS AS LINHAS DA MESMA SEPARAÇÃO
            let qtdLinhasAtualizadas = 0;

            state.dados.forEach((d, idx) => {
                // Atualizar apenas linhas com mesmo separacao_lote_id
                if (d.separacao_lote_id === separacaoLoteId) {
                    // Atualizar estado local
                    state.dados[idx].agendamento_confirmado = novoEstado;
                    qtdLinhasAtualizadas++;

                    // Atualizar UI do botão
                    const btnConfirmar = document.querySelector(`button.btn-confirmar[data-row-index="${idx}"]`);
                    if (btnConfirmar) {
                        if (novoEstado) {
                            // Confirmado
                            btnConfirmar.classList.remove('btn-primary');
                            btnConfirmar.classList.add('btn-success');
                            btnConfirmar.textContent = '✓';
                            btnConfirmar.title = 'Clique para desconfirmar';
                        } else {
                            // Não confirmado
                            btnConfirmar.classList.remove('btn-success');
                            btnConfirmar.classList.add('btn-primary');
                            btnConfirmar.textContent = '⏱';
                            btnConfirmar.title = 'Confirmar agendamento';
                        }
                    }
                }
            });

            // ✅ Removido toast de confirmação para agilizar fluxo
            // const mensagem = novoEstado
            //     ? `Agendamento confirmado (${qtdLinhasAtualizadas} ${qtdLinhasAtualizadas === 1 ? 'linha' : 'linhas'})`
            //     : `Confirmação removida (${qtdLinhasAtualizadas} ${qtdLinhasAtualizadas === 1 ? 'linha' : 'linhas'})`;
            // mostrarMensagem('Sucesso', mensagem, 'success');

        } catch (erro) {
            console.error('Erro ao alternar confirmação de agendamento:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        }
    }

    /**
     * Mostrar totais do protocolo em um toast
     */
    async function mostrarTotaisProtocolo(protocolo) {
        // Se não houver protocolo, mostrar mensagem
        if (!protocolo || protocolo.trim() === '') {
            mostrarToast('⚠️ Sem protocolo', 'Esta linha não possui protocolo informado', 'warning');
            return;
        }

        try {
            // Buscar totais via API
            const response = await fetch(`/carteira/simples/api/totais-protocolo?protocolo=${encodeURIComponent(protocolo)}`);

            if (!response.ok) {
                throw new Error('Erro ao buscar totais do protocolo');
            }

            const dados = await response.json();

            if (dados.erro) {
                mostrarToast('❌ Erro', dados.erro, 'danger');
                return;
            }

            // Formatar valores para exibição
            const valorTotal = new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(dados.valor_total || 0);

            const pesoTotal = new Intl.NumberFormat('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(dados.peso_total || 0);

            const palletTotal = new Intl.NumberFormat('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(dados.pallet_total || 0);

            const qtdSeparacoes = dados.qtd_separacoes || 0;

            // Montar mensagem do toast
            const mensagem = `
                <strong>Protocolo:</strong> ${protocolo}<br>
                <strong>Separações:</strong> ${qtdSeparacoes}<br>
                <hr class="my-1">
                <strong>💰 Valor Total:</strong> ${valorTotal}<br>
                <strong>⚖️ Peso Total:</strong> ${pesoTotal} kg<br>
                <strong>📦 Pallets Total:</strong> ${palletTotal}
            `;

            mostrarToast('📊 Totais do Protocolo', mensagem, 'info', 2000);

        } catch (erro) {
            console.error('Erro ao buscar totais do protocolo:', erro);
            mostrarToast('❌ Erro', 'Não foi possível buscar os totais do protocolo', 'danger');
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
                // 🔧 CORREÇÃO: Ler do state.dados PRIMEIRO, com fallback para DOM
                // Isso garante que funcione mesmo sem elementos DOM renderizados (Virtual Scrolling)
                let qtdEditavel = d.qtd_editavel || 0;
                let expedicao = d.expedicao_editavel || '';
                let agendamento = d.agendamento_editavel || '';
                let protocolo = d.protocolo_editavel || '';

                // Fallback para DOM se state não tiver valores
                if (!qtdEditavel) {
                    const qtdInput = document.getElementById(`qtd-edit-${idx}`);
                    qtdEditavel = qtdInput ? parseFloat(qtdInput.value || 0) : 0;
                }
                if (!expedicao) {
                    const dataExpedicaoInput = document.getElementById(`dt-exped-${idx}`);
                    expedicao = dataExpedicaoInput ? dataExpedicaoInput.value : '';
                }
                if (!agendamento) {
                    const agendamentoInput = document.getElementById(`dt-agend-${idx}`);
                    agendamento = agendamentoInput ? agendamentoInput.value : '';
                }
                if (!protocolo) {
                    const protocoloInput = document.getElementById(`protocolo-${idx}`);
                    protocolo = protocoloInput ? protocoloInput.value.trim() : '';
                }

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

            // 🔧 CORREÇÃO: Log detalhado para debug
            console.log(`📦 Enviados ${produtosDoPedido.length} produtos, criados ${resultado.qtd_itens} separação(ões)`);

            // 🔧 CORREÇÃO: Mostrar alerta se houve itens rejeitados
            if (resultado.itens_rejeitados && resultado.itens_rejeitados.length > 0) {
                console.warn('⚠️ Itens rejeitados:', resultado.itens_rejeitados);
                mostrarToast('Atenção',
                    `${resultado.itens_rejeitados.length} item(s) não foram criados. Verifique o console para detalhes.`,
                    'warning', 5000);
            }

            // ✅ ATUALIZAÇÃO LOCAL SEM RELOAD
            if (resultado.separacoes && resultado.separacoes.length > 0) {
                // Adicionar separações em state.dados
                resultado.separacoes.forEach(sep => {
                    state.dados.push(sep);
                });

                // Atualizar qtd_saldo dos pedidos correspondentes
                resultado.separacoes.forEach(sep => {
                    atualizarQtdPedidoAposEdicaoSeparacao(sep.num_pedido, sep.cod_produto);
                });

                // Zerar campos editáveis dos pedidos
                // 🔧 CORREÇÃO: Limpar também os campos no state.dados
                state.dados.forEach((item, index) => {
                    if (item.tipo === 'pedido' && item.num_pedido === numPedido) {
                        // Limpar state.dados
                        item.qtd_editavel = 0;
                        item.expedicao_editavel = '';
                        item.agendamento_editavel = '';
                        item.protocolo_editavel = '';

                        // Limpar DOM se existir
                        const qtdInput = document.getElementById(`qtd-edit-${index}`);
                        const dtExpedInput = document.getElementById(`dt-exped-${index}`);
                        if (qtdInput) qtdInput.value = 0;
                        if (dtExpedInput) dtExpedInput.value = '';
                    }
                });

                // ✅ RECALCULAR ESTOQUES dos produtos afetados
                if (resultado.produtos_afetados && resultado.produtos_afetados.length > 0) {
                    resultado.produtos_afetados.forEach(codProduto => {
                        recalcularTodasLinhasProduto(codProduto);
                    });
                }

                // Verificar visibilidade (ocultar pedidos com saldo=0)
                resultado.separacoes.forEach(sep => {
                    verificarVisibilidadeLinhas(sep.cod_produto, sep.num_pedido);
                });

                // Renderizar novas linhas de separação se estiver na área visível
                renderizarNovasSeparacoes(resultado.separacoes);

                console.log(`✅ ${resultado.separacoes.length} separação(ões) adicionada(s) localmente (sem reload)`);
            }

        } catch (erro) {
            console.error('Erro ao criar nova separação:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        } finally {
            mostrarLoading(false);
        }
    }

    // ✅ NOVA FUNÇÃO: Renderizar novas separações na tabela
    function renderizarNovasSeparacoes(separacoes) {
        const tbody = document.getElementById('tbody-carteira');
        if (!tbody) return;

        separacoes.forEach(sep => {
            // Encontrar índice correto em state.dados
            const indexNoState = state.dados.findIndex(d => d.tipo === 'separacao' && d.id === sep.id);

            if (indexNoState === -1) {
                console.warn(`⚠️ Separação ${sep.id} não encontrada em state.dados`);
                return;
            }

            // Verificar se já existe no DOM
            const linhaExistente = document.getElementById(`row-sep-${indexNoState}`);
            if (linhaExistente) {
                console.log(`✅ Separação ${sep.id} já renderizada no DOM`);
                return; // Já existe
            }

            // Renderizar nova linha
            const html = renderizarLinhaSeparacao(sep, indexNoState);

            // 🔴 CORREÇÃO: Usar table/tbody para criar <tr> corretamente
            const tempTable = document.createElement('table');
            const tempTbody = document.createElement('tbody');
            tempTable.appendChild(tempTbody);
            tempTbody.innerHTML = html;
            const novaLinha = tempTbody.firstElementChild;

            if (novaLinha) {
                // Inserir após a linha do pedido correspondente
                const todasLinhasPedido = Array.from(document.querySelectorAll(`tr[data-num-pedido="${sep.num_pedido}"]`))
                    .filter(row => row.id.startsWith('row-') && row.dataset.tipo === 'pedido');  // Apenas PEDIDOS

                // Buscar última linha do produto específico
                const linhasProduto = todasLinhasPedido.filter(row => row.dataset.codProduto === sep.cod_produto);
                const pedidoRow = linhasProduto.length > 0 ? linhasProduto[linhasProduto.length - 1] : todasLinhasPedido[todasLinhasPedido.length - 1];

                if (pedidoRow) {
                    pedidoRow.after(novaLinha);
                } else {
                    tbody.appendChild(novaLinha);
                }

                // Renderizar estoque da nova linha
                try {
                    renderizarEstoquePrecalculado(indexNoState, sep);
                } catch (erro) {
                    console.error(`Erro ao renderizar estoque da nova separação ${indexNoState}:`, erro);
                }

                console.log(`✅ Separação ${sep.id} renderizada no DOM (index ${indexNoState})`);
            }
        });
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

            // ✅ Removido toast de confirmação para agilizar fluxo
            // Montar mensagem descritiva
            // let mensagem = resultado.message;
            //
            // // Adicionar detalhes se houver atualizações
            // if (resultado.itens_atualizados && resultado.itens_atualizados.length > 0) {
            //     mensagem += '<br><br><small class="text-muted">Detalhes das atualizações:</small><br>';
            //     resultado.itens_atualizados.forEach(item => {
            //         mensagem += `<small>• ${item.cod_produto}: ${item.quantidade_anterior} + ${item.quantidade_adicionada} = ${item.quantidade_nova}</small><br>`;
            //     });
            // }
            //
            // mostrarMensagem('Sucesso', mensagem, 'success');

            // ✅ ATUALIZAÇÃO LOCAL SEM RELOAD
            if (resultado.separacoes && resultado.separacoes.length > 0) {
                // Atualizar/adicionar separações em state.dados
                resultado.separacoes.forEach(sepNova => {
                    // Verificar se já existe em state.dados
                    const indexExistente = state.dados.findIndex(
                        d => d.tipo === 'separacao' && d.id === sepNova.id
                    );

                    if (indexExistente >= 0) {
                        // Atualizar existente
                        Object.assign(state.dados[indexExistente], sepNova);

                        // Atualizar UI da linha se estiver renderizada
                        const row = document.getElementById(`row-sep-${indexExistente}`);
                        if (row) {
                            const qtdInput = document.getElementById(`qtd-sep-${indexExistente}`);
                            if (qtdInput) qtdInput.value = Math.round(sepNova.qtd_saldo);
                            row.querySelector('.valor-total').textContent = formatarMoeda(sepNova.valor_saldo);
                            row.querySelector('.pallets').textContent = formatarNumero(sepNova.pallet, 2);
                            row.querySelector('.peso').textContent = Math.round(sepNova.peso);
                        }
                    } else {
                        // Adicionar nova
                        state.dados.push(sepNova);
                    }
                });

                // Atualizar qtd_saldo dos pedidos correspondentes
                resultado.separacoes.forEach(sep => {
                    atualizarQtdPedidoAposEdicaoSeparacao(sep.num_pedido, sep.cod_produto);
                });

                // Zerar campos editáveis dos pedidos
                // 🔧 CORREÇÃO: Limpar também os campos no state.dados
                state.dados.forEach((item, index) => {
                    if (item.tipo === 'pedido' && item.num_pedido === numPedido) {
                        // Limpar state.dados
                        item.qtd_editavel = 0;
                        item.expedicao_editavel = '';
                        item.agendamento_editavel = '';
                        item.protocolo_editavel = '';

                        // Limpar DOM se existir
                        const qtdInput = document.getElementById(`qtd-edit-${index}`);
                        const dtExpedInput = document.getElementById(`dt-exped-${index}`);
                        if (qtdInput) qtdInput.value = 0;
                        if (dtExpedInput) dtExpedInput.value = '';
                    }
                });

                // Recalcular estoques dos produtos afetados
                if (resultado.produtos_afetados && resultado.produtos_afetados.length > 0) {
                    resultado.produtos_afetados.forEach(codProduto => {
                        recalcularTodasLinhasProduto(codProduto);
                    });
                }

                // Verificar visibilidade
                resultado.separacoes.forEach(sep => {
                    verificarVisibilidadeLinhas(sep.cod_produto, sep.num_pedido);
                });

                // Renderizar novas separações se houver
                const novasSeparacoes = resultado.separacoes.filter(sep => {
                    return !state.dados.some((d, idx) => {
                        return d.tipo === 'separacao' && d.id === sep.id && idx < state.dados.length - resultado.separacoes.length;
                    });
                });

                if (novasSeparacoes.length > 0) {
                    renderizarNovasSeparacoes(novasSeparacoes);
                }

                console.log(`✅ Itens adicionados/atualizados localmente (sem reload)`);
            }

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
     *
     * 🚀 OTIMIZADO: Usa índices de lookup O(k) em vez de O(n).
     * SEGURANÇA: Lê dados frescos do state.dados (não cache).
     */
    function recalcularTodasLinhasProduto(codProduto) {
        // Buscar códigos unificados (inclui o próprio código)
        const codigosUnificados = state.mapaUnificacao[codProduto] || [codProduto];

        // Iterar apenas sobre índices relevantes (O(k) em vez de O(n))
        codigosUnificados.forEach(codigo => {
            const indices = state.indices.porProduto.get(codigo) || [];
            indices.forEach(index => {
                const item = state.dados[index];
                renderizarEstoquePrecalculado(index, item);
            });
        });
    }

    /**
     * 🆕 COLETA TODAS AS SAÍDAS de um produto (PEDIDOS editáveis + SEPARAÇÕES).
     * ✅ SEM DUPLICAÇÃO: Separações JÁ estão no state.dados.
     * ✅ COM UNIFICAÇÃO: Busca saídas de TODOS os códigos unificados.
     * Retorna array de saídas: [{data, qtd}, ...]
     *
     * 🚀 OTIMIZADO: Usa índices de lookup O(k) em vez de O(n).
     * SEGURANÇA: Lê valores FRESCOS do DOM (não cache).
     */
    function coletarTodasSaidas(codProduto) {
        const saidas = [];
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        const hojeStr = hoje.toISOString().split('T')[0];

        // ✅ OBTER CÓDIGOS UNIFICADOS (incluindo o próprio código)
        const codigosUnificados = state.mapaUnificacao[codProduto] || [codProduto];

        // ============================================
        // PARTE 1: COLETAR SAÍDAS VISÍVEIS (via índices)
        // 🚀 OTIMIZADO: O(k) em vez de O(n)
        // ============================================
        codigosUnificados.forEach(codigo => {
            // Usar índice de lookup em vez de iterar todos os dados
            const indices = state.indices.porProduto.get(codigo) || [];

            indices.forEach(index => {
                const item = state.dados[index];
                let qtd = 0;
                let data = null;

                if (item.tipo === 'separacao') {
                    // ✅ SEPARAÇÕES: Coletar qtd_saldo + expedicao de state.dados
                    qtd = parseFloat(item.qtd_saldo) || 0;
                    data = item.expedicao;
                } else {
                    // ✅ PEDIDOS: Buscar inputs editáveis (LEITURA FRESCA DO DOM)
                    const qtdInput = document.getElementById(`qtd-edit-${index}`);
                    const dataInput = document.getElementById(`dt-exped-${index}`);

                    if (qtdInput && dataInput) {
                        qtd = parseFloat(qtdInput.value || 0);
                        data = dataInput.value;
                    }
                }

                // ✅ CORREÇÃO: Agrupar separações atrasadas (data < hoje) ou sem data em D0 (hoje)
                if (qtd > 0) {
                    if (!data) {
                        // Sem data → D0 (hoje)
                        data = hojeStr;
                    } else {
                        const dataExpedicao = new Date(data + 'T00:00:00');
                        if (dataExpedicao < hoje) {
                            // Atrasada → D0 (hoje)
                            data = hojeStr;
                        }
                    }

                    saidas.push({
                        data: data,
                        qtd: qtd
                    });
                }
            });

            // ============================================
            // PARTE 2: 🆕 ADICIONAR SAÍDAS NÃO VISÍVEIS (backend)
            // ============================================
            const saidasNaoVisiveis = state.saidasNaoVisiveis[codigo] || [];
            if (saidasNaoVisiveis.length > 0) {
                saidas.push(...saidasNaoVisiveis);
            }
        });

        return saidas;
    }

    /**
     * 🆕 CALCULA PROJEÇÃO COMPLETA DE ESTOQUE (100% front-end).
     *
     * Considera:
     * - Estoque atual (físico)
     * - Saídas: PEDIDOS editáveis + SEPARAÇÕES (sincronizado_nf=False)
     * - Entradas: Programação de produção
     *
     * @param {Number} estoqueAtual - Estoque físico atual
     * @param {Array} saidas - Array [{data, qtd}, ...] de TODAS as saídas
     * @param {Array} entradas - Array [{data, qtd}, ...] de programação
     * @returns {Object} {projecao: [...], menor_estoque_d7: number}
     */
    function calcularProjecaoCompleta(estoqueAtual = 0, saidas = [], entradas = []) {
        // 🚀 OTIMIZADO: Reduzido de 5 loops para 4 loops com Map de índices
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);

        const projecao = [];
        const dateIndex = new Map(); // 🚀 Map para lookup O(1) por data

        // Loop 1: Criar estrutura de 29 dias + Map de índices
        for (let dia = 0; dia <= 28; dia++) {
            const data = new Date(hoje);
            data.setDate(data.getDate() + dia);
            const dataStr = data.toISOString().split('T')[0];

            dateIndex.set(dataStr, dia); // O(1) lookup
            projecao.push({
                dia: dia,
                data: dataStr,
                saldo_inicial: 0,
                entrada: 0,
                saida: 0,
                saldo: 0,
                saldo_final: 0
            });
        }

        // Loop 2: Processar saídas diretamente no array (sem objeto intermediário)
        saidas.forEach(s => {
            const idx = dateIndex.get(s.data);
            if (idx !== undefined) {
                projecao[idx].saida += s.qtd;
            }
            // Saídas fora do range de 29 dias são ignoradas (comportamento mantido)
        });

        // Loop 3: Processar entradas diretamente (com D+1)
        entradas.forEach(e => {
            // ✅ ENTRADA EM D+1 (apenas na Carteira Simples)
            const dataEntrada = new Date(e.data + 'T00:00:00');
            dataEntrada.setDate(dataEntrada.getDate() + 1);
            const dataEntradaStr = dataEntrada.toISOString().split('T')[0];

            const idx = dateIndex.get(dataEntradaStr);
            if (idx !== undefined) {
                projecao[idx].entrada += e.qtd;
            }
        });

        // Loop 4: Calcular saldo_final em cascata (sequencial por natureza)
        let menorEstoque = estoqueAtual;

        for (let i = 0; i < projecao.length; i++) {
            const proj = projecao[i];

            if (i === 0) {
                // D0: saldo_inicial = estoque atual
                proj.saldo_inicial = estoqueAtual;
            } else {
                // D+N: saldo_inicial = saldo_final do dia anterior
                proj.saldo_inicial = projecao[i - 1].saldo_final;
            }

            // Calcular saldos
            proj.saldo = proj.saldo_inicial - proj.saida; // Sem produção
            proj.saldo_final = proj.saldo + proj.entrada; // Com produção

            // Atualizar menor estoque
            if (proj.saldo_final < menorEstoque) {
                menorEstoque = proj.saldo_final;
            }
        }

        // Calcular menor_estoque_d7 (primeiros 8 dias: D0 a D7)
        const menor_estoque_d7 = Math.min(
            ...projecao.slice(0, 8).map(p => p.saldo_final)
        );

        return {
            projecao: projecao,
            menor_estoque_d7: menor_estoque_d7
        };
    }

    // ==============================================
    // ESTOQUE PROJETADO
    // ==============================================

    /**
     * 🆕 RENDERIZA ESTOQUE COM CÁLCULO 100% FRONT-END
     */
    function renderizarEstoquePrecalculado(rowIndex, item) {
        // 1. Coletar TODAS as saídas (pedidos editáveis + separações)
        const saidas = coletarTodasSaidas(item.cod_produto);

        // 2. Obter programação de produção (entradas futuras)
        const programacao = item.programacao || [];

        // 3. Calcular projeção completa (100% front-end)
        const estoqueAtual = item.estoque_atual || 0;
        const resultado = calcularProjecaoCompleta(estoqueAtual, saidas, programacao);

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

        // ✅ PROTEÇÃO: Se elemento não existe (linha não renderizada ou oculta), sair silenciosamente
        if (!container) {
            return; // Linha não está no DOM (virtual scrolling ou oculta)
        }

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
            if (item.estoque_atual !== undefined) {
                // Recalcular com cálculo completo (100% front-end)
                const saidas = coletarTodasSaidas(item.cod_produto);
                const programacao = item.programacao || [];
                const estoqueAtual = item.estoque_atual || 0;
                const resultado = calcularProjecaoCompleta(estoqueAtual, saidas, programacao);

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

    /**
     * 🆕 Escapa caracteres HTML para evitar XSS em tooltips
     */
    function escapeHtml(texto) {
        if (!texto) return '';
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }

    /**
     * 🆕 Monta ícone de tags com popover mostrando badges coloridos
     * @param {string|null} tagsJson - JSON string das tags do Odoo
     * @returns {string} HTML do ícone ou vazio
     */
    function montarIconeTags(tagsJson) {
        if (!tagsJson) return '';

        try {
            const tags = JSON.parse(tagsJson);
            if (!tags || tags.length === 0) return '';

            // Mapa de cores do Odoo para CSS
            const coresOdoo = {
                0: '#6c757d',   // Cinza
                1: '#dc3545',   // Vermelho
                2: '#fd7e14',   // Laranja
                3: '#ffc107',   // Amarelo
                4: '#20c997',   // Verde-água
                5: '#198754',   // Verde
                6: '#0dcaf0',   // Ciano
                7: '#0d6efd',   // Azul
                8: '#6f42c1',   // Roxo
                9: '#d63384',   // Rosa
                10: '#495057',  // Cinza escuro
                11: '#343a40'   // Preto
            };

            // Montar lista de badges para o popover
            const badgesHtml = tags.map(tag => {
                const cor = coresOdoo[tag.color] || '#6c757d';
                const corTexto = [3, 6].includes(tag.color) ? '#212529' : '#ffffff';
                return `<span class="badge me-1" style="background-color: ${cor}; color: ${corTexto}; font-size: 9px;">${escapeHtml(tag.name)}</span>`;
            }).join('');

            // Primeira tag como título do ícone
            const primeiraTag = tags[0].name;
            const quantidadeTags = tags.length;

            return `<span class="icone-info icone-tags"
                tabindex="0"
                data-bs-toggle="popover"
                data-bs-trigger="hover focus"
                data-bs-html="true"
                data-bs-content="${escapeHtml(badgesHtml)}"
                title="${quantidadeTags} tag${quantidadeTags > 1 ? 's' : ''}: ${escapeHtml(primeiraTag)}${quantidadeTags > 1 ? '...' : ''}">🏷️</span>`;
        } catch (e) {
            console.warn('Erro ao parsear tags_pedido:', e);
            return '';
        }
    }

    function inicializarTooltips() {
        const tooltips = document.querySelectorAll('.truncate-tooltip');
        tooltips.forEach(el => {
            el.title = el.title || el.textContent;
        });

        // 🆕 Inicializar tooltips Bootstrap para ícones de observação
        const iconesObs = document.querySelectorAll('.icone-obs[data-bs-toggle="tooltip"]');
        iconesObs.forEach(el => {
            new bootstrap.Tooltip(el, {
                container: 'body',
                boundary: 'viewport'
            });
        });

        // 🆕 Inicializar popovers Bootstrap para ícones de tags
        const iconesTags = document.querySelectorAll('.icone-tags[data-bs-toggle="popover"]');
        iconesTags.forEach(el => {
            new bootstrap.Popover(el, {
                container: 'body',
                boundary: 'viewport',
                sanitize: false  // Permitir HTML nos badges
            });
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

    // ==============================================
    // FUNÇÕES DE STANDBY
    // ==============================================

    /**
     * Abre o modal de seleção de tipo de standby
     * @param {string} numPedido - Número do pedido a enviar para standby
     */
    function abrirModalStandby(numPedido) {
        const modal = document.getElementById('modalStandby');
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);

        // Preencher número do pedido no modal
        document.getElementById('modalStandbyPedido').textContent = numPedido;

        // Configurar event listeners para os botões de tipo
        const botoesTipo = modal.querySelectorAll('.btn-standby-tipo');
        botoesTipo.forEach(btn => {
            // Remover listeners anteriores
            const novoBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(novoBtn, btn);

            // Adicionar novo listener
            novoBtn.addEventListener('click', async () => {
                const tipoStandby = novoBtn.dataset.tipo;
                await enviarParaStandby(numPedido, tipoStandby);
                bsModal.hide();
            });
        });

        bsModal.show();
    }

    /**
     * Envia um pedido para standby via API
     * @param {string} numPedido - Número do pedido
     * @param {string} tipoStandby - Tipo de standby (Saldo, Aguardar Comercial, Aguardar PCP)
     */
    async function enviarParaStandby(numPedido, tipoStandby) {
        try {
            // Mostrar loading
            const modalLoading = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalLoading'));
            modalLoading.show();

            const response = await fetch('/carteira/api/standby/criar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    tipo_standby: tipoStandby
                })
            });

            const resultado = await response.json();
            modalLoading.hide();

            if (resultado.success) {
                mostrarToast('Sucesso', `Pedido ${numPedido} enviado para standby (${tipoStandby})`, 'success');
                // Recarregar dados para remover o pedido da lista
                await carregarDados();
            } else {
                mostrarMensagem('Erro', resultado.message || 'Erro ao enviar para standby', 'danger');
            }

        } catch (erro) {
            console.error('Erro ao enviar para standby:', erro);
            const modalLoading = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalLoading'));
            modalLoading.hide();
            mostrarMensagem('Erro', `Erro ao enviar para standby: ${erro.message}`, 'danger');
        }
    }

    /**
     * Mostrar toast de notificação
     * @param {string} titulo - Título do toast
     * @param {string} mensagem - Mensagem do toast (aceita HTML)
     * @param {string} tipo - Tipo: success, danger, warning, info
     * @param {number} duracao - Duração em ms (padrão: 5000)
     */
    function mostrarToast(titulo, mensagem, tipo = 'info', duracao = 5000) {
        const toastElement = document.getElementById('toastProtocolo');
        const toastTitulo = document.getElementById('toastProtocoloTitulo');
        const toastMensagem = document.getElementById('toastProtocoloMensagem');

        // Configurar conteúdo
        toastTitulo.textContent = titulo;
        toastMensagem.innerHTML = mensagem;

        // Aplicar classes de cor
        const header = toastElement.querySelector('.toast-header');
        header.className = `toast-header bg-${tipo} text-white`;

        // Criar e mostrar o toast
        const bsToast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: duracao
        });

        bsToast.show();
    }

    // ==============================================
    // 🆕 FUNCIONALIDADE 1: TOAST TOTAIS DA SEPARAÇÃO
    // ==============================================
    function mostrarToastTotaisSeparacao(separacaoLoteId) {
        // Buscar todas as separações com o mesmo lote_id
        const separacoesDoLote = state.dados.filter(item =>
            item.tipo === 'separacao' && item.separacao_lote_id === separacaoLoteId
        );

        if (separacoesDoLote.length === 0) {
            console.warn('⚠️ Nenhuma separação encontrada para lote:', separacaoLoteId);
            return;
        }

        // Calcular totais
        let totalValor = 0;
        let totalPeso = 0;
        let totalPallet = 0;
        let qtdItens = separacoesDoLote.length;

        separacoesDoLote.forEach(sep => {
            totalValor += parseFloat(sep.valor_total || 0);
            totalPeso += parseFloat(sep.peso || 0);
            totalPallet += parseFloat(sep.pallets || 0);
        });

        // Pegar dados da primeira separação para contexto
        const primeira = separacoesDoLote[0];
        const loteIdCurto = separacaoLoteId.slice(-10); // Últimos 10 dígitos

        // Criar toast HTML
        const toastHtml = `
            <div class="toast align-items-center border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true"
                 style="position: fixed; top: 80px; right: 20px; z-index: 1050; min-width: 320px;"
                 id="toast-totais-separacao">
                <div class="d-flex">
                    <div class="toast-body bg-tertiary-custom" style="border-radius: 8px;">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong style="font-size: 13px;">📦 TOTAIS DA SEPARAÇÃO</strong>
                            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                        </div>
                        <hr style="margin: 8px 0; border-color: var(--bs-border-color);">
                        <div style="font-size: 11px; line-height: 1.6;">
                            <div class="mb-1"><strong>Lote:</strong> ${loteIdCurto}</div>
                            <div class="mb-1"><strong>Cliente:</strong> ${primeira.raz_social_red || 'N/A'}</div>
                            <div class="mb-1"><strong>Expedição:</strong> ${primeira.expedicao ? formatarData(primeira.expedicao) : 'N/A'}</div>
                            <hr style="margin: 8px 0; border-color: var(--bs-border-color);">
                            <div class="mb-1">📦 <strong>Itens:</strong> ${qtdItens}</div>
                            <div class="mb-1">💰 <strong>Valor:</strong> R$ ${Math.round(totalValor).toLocaleString('pt-BR')}</div>
                            <div class="mb-1">⚖️ <strong>Peso:</strong> ${Math.round(totalPeso).toLocaleString('pt-BR')} kg</div>
                            <div>📦 <strong>Pallet:</strong> ${totalPallet.toFixed(2)} PLT</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remover toast anterior se existir
        const toastAntigo = document.getElementById('toast-totais-separacao');
        if (toastAntigo) {
            toastAntigo.remove();
        }

        // Inserir no DOM
        document.body.insertAdjacentHTML('beforeend', toastHtml);

        // Inicializar e exibir toast
        const toastElement = document.getElementById('toast-totais-separacao');
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 6000 // 6 segundos
        });
        toast.show();

        // Remover do DOM após fechar
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });

        console.log(`✅ Toast exibido para lote ${loteIdCurto}: ${qtdItens} itens, R$ ${totalValor.toFixed(2)}`);
    }

    // ==============================================
    // 🆕 FUNCIONALIDADE 2: RASTREAMENTO DE PRODUTO
    // ==============================================
    async function rastrearProduto(codProduto) {
        try {
            const response = await fetch(`/carteira/simples/api/rastrear-produto?cod_produto=${encodeURIComponent(codProduto)}`);
            const resultado = await response.json();

            if (!resultado.success) {
                mostrarMensagem('Erro', resultado.error || 'Erro ao rastrear produto', 'danger');
                return;
            }

            // 🆕 Abrir modal com os dados completos (incluindo códigos unificados)
            abrirModalRastreamento(codProduto, resultado.separacoes, resultado.codigos_unificados || [codProduto]);

        } catch (erro) {
            console.error('Erro ao rastrear produto:', erro);
            mostrarMensagem('Erro', `Erro ao rastrear produto: ${erro.message}`, 'danger');
        }
    }

    function abrirModalRastreamento(codProduto, separacoes, codigosUnificados = []) {
        // Criar modal se não existir
        let modal = document.getElementById('modalRastreamentoProduto');

        if (!modal) {
            const modalHtml = `
                <div class="modal fade" id="modalRastreamentoProduto" tabindex="-1">
                    <div class="modal-dialog modal-xl modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">
                                    <i class="fas fa-search me-2"></i>
                                    Saídas Programadas: <span id="modal-rastreamento-codigo"></span>
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div id="modal-rastreamento-unificados">
                                    <!-- 🆕 Códigos unificados serão exibidos aqui -->
                                </div>
                                <div id="modal-rastreamento-conteudo">
                                    <!-- Será preenchido dinamicamente -->
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modal = document.getElementById('modalRastreamentoProduto');
        }

        // Atualizar código do produto no título
        document.getElementById('modal-rastreamento-codigo').textContent = codProduto;

        // 🆕 Exibir informação sobre códigos unificados
        const unificadosContainer = document.getElementById('modal-rastreamento-unificados');
        if (codigosUnificados.length > 1) {
            unificadosContainer.innerHTML = `
                <div class="alert alert-warning mb-3">
                    <i class="fas fa-link me-2"></i>
                    <strong>Códigos Unificados:</strong> Este produto possui ${codigosUnificados.length} códigos equivalentes.
                    <br>
                    <small class="text-muted">
                        ${codigosUnificados.map(cod =>
                            cod === codProduto
                                ? `<strong>${cod}</strong>`
                                : cod
                        ).join(' | ')}
                    </small>
                </div>
            `;
        } else {
            unificadosContainer.innerHTML = '';
        }

        // Gerar conteúdo da tabela
        const conteudo = document.getElementById('modal-rastreamento-conteudo');

        if (!separacoes || separacoes.length === 0) {
            conteudo.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Nenhuma separação ativa encontrada para este produto${codigosUnificados.length > 1 ? ' (incluindo códigos unificados)' : ''}.
                </div>
            `;
        } else {
            // Calcular totais
            const totalQtd = separacoes.reduce((sum, s) => sum + parseFloat(s.qtd_saldo || 0), 0);
            const totalValor = separacoes.reduce((sum, s) => sum + parseFloat(s.valor_saldo || 0), 0);

            // 🆕 Verificar se há múltiplos códigos nas separações
            const temMultiplosCodigos = codigosUnificados.length > 1;

            conteudo.innerHTML = `
                <div class="alert alert-success mb-3">
                    <strong>Total de separações encontradas:</strong> ${separacoes.length} |
                    <strong>Quantidade total:</strong> ${Math.round(totalQtd).toLocaleString('pt-BR')} |
                    <strong>Valor total:</strong> R$ ${Math.round(totalValor).toLocaleString('pt-BR')}
                </div>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered table-hover">
                        <thead class="table-dark">
                            <tr>
                                ${temMultiplosCodigos ? '<th style="min-width: 80px;">Código</th>' : ''}
                                <th style="min-width: 100px;">Lote ID</th>
                                <th style="min-width: 150px;">Cliente</th>
                                <th style="min-width: 80px;">Qtd</th>
                                <th style="min-width: 100px;">Data Expedição</th>
                                <th style="min-width: 100px;">Valor</th>
                                <th style="min-width: 80px;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${separacoes.map(sep => {
                                const loteIdCurto = sep.separacao_lote_id ? sep.separacao_lote_id.slice(-10) : 'N/A';
                                const statusBadge = obterBadgeStatus(sep.status_calculado || sep.status || 'ABERTO');
                                // 🆕 Destacar se código é diferente do pesquisado
                                const codigoDestaque = sep.cod_produto !== codProduto
                                    ? `<span class="badge bg-info">${sep.cod_produto}</span>`
                                    : `<code>${sep.cod_produto}</code>`;

                                return `
                                    <tr>
                                        ${temMultiplosCodigos ? `<td>${codigoDestaque}</td>` : ''}
                                        <td><code>${loteIdCurto}</code></td>
                                        <td>${sep.raz_social_red || 'N/A'}</td>
                                        <td class="text-end">${Math.round(sep.qtd_saldo || 0).toLocaleString('pt-BR')}</td>
                                        <td>${sep.expedicao ? formatarData(sep.expedicao) : 'N/A'}</td>
                                        <td class="text-end">R$ ${Math.round(sep.valor_saldo || 0).toLocaleString('pt-BR')}</td>
                                        <td>${statusBadge}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        // Exibir modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        bsModal.show();
    }

    function obterBadgeStatus(status) {
        const statusMap = {
            'PREVISAO': '<span class="badge bg-secondary">PREVISÃO</span>',
            'ABERTO': '<span class="badge bg-warning text-dark">ABERTO</span>',
            'COTADO': '<span class="badge bg-info text-dark">COTADO</span>',
            'EMBARCADO': '<span class="badge bg-primary">EMBARCADO</span>',
            'FATURADO': '<span class="badge bg-success">FATURADO</span>',
            'NF no CD': '<span class="badge bg-danger">NF no CD</span>',
            'Atrasado': '<span class="badge bg-danger">ATRASADO</span>'
        };
        return statusMap[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    // ==============================================
    // 🆕 FUNCIONALIDADE 3: FILTRO SEP./PDD.
    // ==============================================
    function aplicarFiltroTipo() {
        const checkboxSep = document.getElementById('filtro-tipo-sep');
        const checkboxPdd = document.getElementById('filtro-tipo-pdd');

        if (!checkboxSep || !checkboxPdd) {
            console.warn('⚠️ Checkboxes de filtro tipo não encontrados');
            return;
        }

        const exibirSep = checkboxSep.checked;
        const exibirPdd = checkboxPdd.checked;

        console.log(`🔧 Filtro Tipo: Sep=${exibirSep}, Pdd=${exibirPdd}`);

        // Se nenhum marcado, exibir NADA (Opção B confirmada)
        if (!exibirSep && !exibirPdd) {
            const tbody = document.getElementById('tbody-carteira');
            tbody.innerHTML = `
                <tr>
                    <td colspan="29" class="text-center py-4">
                        <div class="alert alert-warning d-inline-block">
                            <i class="fas fa-exclamation-triangle"></i>
                            <strong>Nenhum tipo selecionado</strong><br>
                            <small>Marque pelo menos "Sep." ou "Pdd." para exibir dados.</small>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        // Filtrar linhas via JavaScript (display: none)
        const tbody = document.getElementById('tbody-carteira');
        const linhas = tbody.querySelectorAll('tr');

        let pedidosOcultadosPorSaldo = 0; // 🆕 Contador para debug

        linhas.forEach(linha => {
            const tipo = linha.dataset.tipo; // 'pedido' ou 'separacao'

            if (!tipo) {
                // Linha de totais ou outras - manter visível
                return;
            }

            // Lógica de visibilidade
            let deveExibir = false;

            if (tipo === 'separacao' && exibirSep) {
                deveExibir = true;
            }

            if (tipo === 'pedido' && exibirPdd) {
                // ✅ CORREÇÃO: Verificar qtd_saldo ANTES de exibir
                const qtdSaldo = parseFloat(linha.dataset.qtdSaldo || linha.getAttribute('data-qtd-saldo') || 0);

                if (qtdSaldo > 0) {
                    deveExibir = true;
                } else {
                    // Pedido com saldo=0 deve permanecer oculto
                    deveExibir = false;
                    pedidosOcultadosPorSaldo++;
                }
            }

            // Aplicar visibilidade
            linha.style.display = deveExibir ? '' : 'none';
        });

        console.log(`✅ Filtro de tipo aplicado: exibindo ${exibirSep ? 'Sep.' : ''} ${exibirPdd ? 'Pdd.' : ''}`);

        if (pedidosOcultadosPorSaldo > 0) {
            console.log(`   ℹ️ ${pedidosOcultadosPorSaldo} pedido(s) com saldo=0 mantidos ocultos`);
        }
    }

})();
