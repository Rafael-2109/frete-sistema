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
        itensPorPagina: 100,
        totalItens: 0,
        estoqueProjetadoCache: {}, // Cache {cod_produto_data: {estoque_atual, projecoes}}
        projecaoEstoqueOffset: 0, // 🆕 OFFSET GLOBAL para paginação D0-D28 (não mais por linha)
        carregando: false, // Flag para evitar múltiplas chamadas simultâneas
        modalLoading: null, // Instância única do modal de loading
    };

    // ==============================================
    // INICIALIZAÇÃO
    // ==============================================
    document.addEventListener('DOMContentLoaded', function() {
        inicializarEventos();
        carregarDados();
    });

    function inicializarEventos() {
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
            atualizarContadores();
            atualizarPaginacao();

        } catch (erro) {
            console.error('Erro ao carregar dados:', erro);
            mostrarMensagem('Erro', `Erro ao carregar dados: ${erro.message}`, 'danger');
        } finally {
            state.carregando = false;
            mostrarLoading(false);
        }
    }

    function aplicarFiltros() {
        try {
            state.filtrosAplicados = {
                num_pedido: document.getElementById('filtro-busca')?.value.trim() || '',
                estado: document.getElementById('filtro-estado')?.value.trim() || '',
                municipio: document.getElementById('filtro-municipio')?.value.trim() || '',
                data_pedido_de: document.getElementById('filtro-data-pedido-de')?.value.trim() || '',
                data_pedido_ate: document.getElementById('filtro-data-pedido-ate')?.value.trim() || '',
                data_entrega_de: document.getElementById('filtro-data-entrega-de')?.value.trim() || '',
                data_entrega_ate: document.getElementById('filtro-data-entrega-ate')?.value.trim() || '',
            };

            state.paginaAtual = 1;
            state.projecaoEstoqueOffset = 0; // 🆕 RESETAR offset global
            carregarDados();
        } catch (erro) {
            console.error('Erro ao aplicar filtros:', erro);
            mostrarMensagem('Erro', 'Erro ao aplicar filtros. Verifique o console.', 'danger');
        }
    }

    function limparFiltros() {
        try {
            const filtroIds = [
                'filtro-busca', 'filtro-estado', 'filtro-municipio',
                'filtro-data-pedido-de', 'filtro-data-pedido-ate',
                'filtro-data-entrega-de', 'filtro-data-entrega-ate'
            ];

            filtroIds.forEach(id => {
                const elemento = document.getElementById(id);
                if (elemento) elemento.value = '';
            });

            state.filtrosAplicados = {};
            state.paginaAtual = 1;
            state.projecaoEstoqueOffset = 0; // 🆕 RESETAR offset global
            carregarDados();
        } catch (erro) {
            console.error('Erro ao limpar filtros:', erro);
            mostrarMensagem('Erro', 'Erro ao limpar filtros. Verifique o console.', 'danger');
        }
    }

    // ==============================================
    // RENDERIZAÇÃO DA TABELA
    // ==============================================
    function renderizarTabela() {
        const tbody = document.getElementById('tbody-carteira');

        if (!state.dados || state.dados.length === 0) {
            tbody.innerHTML = '<tr><td colspan="29" class="text-center py-3">Nenhum registro encontrado</td></tr>';
            return;
        }

        // 🆕 RENDERIZAÇÃO HIERÁRQUICA: pedidos + separações
        const html = state.dados.map((item, index) => {
            if (item.tipo === 'pedido') {
                return renderizarLinha(item, index);
            } else if (item.tipo === 'separacao') {
                return renderizarLinhaSeparacao(item, index);
            }
            return '';
        }).join('');

        tbody.innerHTML = html;

        // Inicializar tooltips
        inicializarTooltips();

        // 🚀 OTIMIZAÇÃO: Renderizar estoques pré-calculados (sem chamadas assíncronas)
        // 🔧 CORREÇÃO: Renderizar SEMPRE, mesmo sem projecoes_estoque (usa saídas adicionais)
        state.dados.forEach((item, index) => {
            try {
                renderizarEstoquePrecalculado(index, item);
            } catch (erro) {
                console.error(`Erro ao renderizar estoque para índice ${index}:`, erro);
            }
        });
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
        if (item.status_calculado === 'ABERTO') {
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
                    <div class="estoque-projecao-container">
                        <button type="button" class="btn-paginacao-estoque btn-prev-dia"
                            data-row-index="${index}">◄</button>
                        <div class="d-flex gap-1" id="projecao-dias-${index}">
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                        </div>
                        <button type="button" class="btn-paginacao-estoque btn-next-dia"
                            data-row-index="${index}">►</button>
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
                    <div class="estoque-projecao-container">
                        <button type="button" class="btn-paginacao-estoque btn-prev-dia"
                            data-row-index="${index}">◄</button>
                        <div class="d-flex gap-1" id="projecao-dias-${index}">
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                            <span class="estoque-dia">-</span>
                        </div>
                        <button type="button" class="btn-paginacao-estoque btn-next-dia"
                            data-row-index="${index}">►</button>
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

        try {
            mostrarLoading(true);

            const response = await fetch('/carteira/simples/api/gerar-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    produtos: produtosDoPedido  // 🆕 Array com produtos que passaram nos verificadores
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
            console.error('Erro ao gerar separação:', erro);
            mostrarMensagem('Erro', erro.message, 'danger');
        } finally {
            mostrarLoading(false);
        }
    }

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

        // 6. Atualizar MENOR 7D
        const menor7dEl = document.getElementById(`menor-7d-${rowIndex}`);
        if (menor7dEl) {
            menor7dEl.textContent = Math.round(resultado.menor_estoque_d7);

            // Aplicar cores
            if (resultado.menor_estoque_d7 < 0) {
                menor7dEl.style.color = 'red';
                menor7dEl.style.fontWeight = 'bold';
            } else if (resultado.menor_estoque_d7 < 100) {
                menor7dEl.style.color = 'orange';
            } else {
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

            // Aplicar cores
            if (estoqueDisponivel < 0) {
                estDataEl.style.color = 'red';
                estDataEl.style.fontWeight = 'bold';
            } else if (estoqueDisponivel < 100) {
                estDataEl.style.color = 'orange';
            } else {
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

        // 🆕 USAR OFFSET GLOBAL (não mais por linha)
        const offset = state.projecaoEstoqueOffset;
        const container = document.getElementById(`projecao-dias-${rowIndex}`);

        // Pegar 7 dias a partir do offset
        const diasVisiveis = projecoes.slice(offset, offset + 7);

        const html = diasVisiveis.map(dia => {
            let classe = 'estoque-dia';
            if (dia.estoque < 0) classe += ' negativo';
            else if (dia.estoque < 100) classe += ' baixo';

            // Extrair dia/mês da data (formato: DD/MM)
            const dataObj = new Date(dia.data + 'T00:00:00');
            const diaDoMes = String(dataObj.getDate()).padStart(2, '0');
            const mes = String(dataObj.getMonth() + 1).padStart(2, '0');
            const diaIndice = dia.dia !== undefined ? `D${dia.dia}` : '';

            return `
                <span class="${classe}" title="${dia.data}">
                    <div style="font-size: 7px;">${diaIndice} ${diaDoMes}/${mes}</div>
                    <div>${formatarNumero(dia.estoque, 0)}</div>
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
    function atualizarContadores() {
        document.getElementById('contador-pedidos').textContent = state.totalItens;

        // Calcular valor total
        const valorTotal = state.dados.reduce((sum, item) => sum + (item.valor_total || 0), 0);
        document.getElementById('valor-total-filtro').textContent = formatarMoeda(valorTotal).replace('R$ ', '');

        // Atualizar info de paginação
        const de = state.totalItens > 0 ? (state.paginaAtual - 1) * state.itensPorPagina + 1 : 0;
        const ate = Math.min(state.paginaAtual * state.itensPorPagina, state.totalItens);

        document.getElementById('info-exibindo-de').textContent = de;
        document.getElementById('info-exibindo-ate').textContent = ate;
        document.getElementById('info-total').textContent = state.totalItens;
    }

    function atualizarPaginacao() {
        const totalPaginas = Math.ceil(state.totalItens / state.itensPorPagina);
        const paginacao = document.getElementById('paginacao');

        if (totalPaginas <= 1) {
            paginacao.innerHTML = '';
            return;
        }

        let html = '';

        // Botão Anterior
        html += `
            <li class="page-item ${state.paginaAtual === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-pagina="${state.paginaAtual - 1}">Anterior</a>
            </li>
        `;

        // Páginas
        const maxPaginas = 5;
        let inicio = Math.max(1, state.paginaAtual - Math.floor(maxPaginas / 2));
        let fim = Math.min(totalPaginas, inicio + maxPaginas - 1);

        if (fim - inicio < maxPaginas - 1) {
            inicio = Math.max(1, fim - maxPaginas + 1);
        }

        for (let i = inicio; i <= fim; i++) {
            html += `
                <li class="page-item ${i === state.paginaAtual ? 'active' : ''}">
                    <a class="page-link" href="#" data-pagina="${i}">${i}</a>
                </li>
            `;
        }

        // Botão Próximo
        html += `
            <li class="page-item ${state.paginaAtual === totalPaginas ? 'disabled' : ''}">
                <a class="page-link" href="#" data-pagina="${state.paginaAtual + 1}">Próximo</a>
            </li>
        `;

        paginacao.innerHTML = html;

        // Event listener
        paginacao.querySelectorAll('a.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const pagina = parseInt(this.dataset.pagina);
                if (pagina >= 1 && pagina <= totalPaginas && pagina !== state.paginaAtual) {
                    state.paginaAtual = pagina;
                    state.projecaoEstoqueOffset = 0; // 🆕 RESETAR offset global ao trocar página
                    carregarDados();
                }
            });
        });
    }

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
