/**
 * JavaScript para Requisições de Compras
 * Módulo: Manufatura
 *
 * Features:
 * - Expansão/colapso de projeção de estoque
 * - Carregamento AJAX de projeção -D7 a +D7
 */

(function () {
    'use strict';

    // ========================================
    // Inicialização
    // ========================================
    document.addEventListener('DOMContentLoaded', function () {
        console.log('[REQUISICOES] Módulo carregado');

        // Inicializar componentes
        inicializarTooltips();
        inicializarFiltros();
        inicializarProjecaoToggle();  // ✅ NOVO
    });

    // ========================================
    // Tooltips Bootstrap
    // ========================================
    function inicializarTooltips() {
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"], [title]')
        );

        tooltipTriggerList.forEach(function (tooltipTriggerEl) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                new bootstrap.Tooltip(tooltipTriggerEl);
            }
        });
    }

    // ========================================
    // Filtros
    // ========================================
    function inicializarFiltros() {
        const formFiltros = document.querySelector('form[action*="listar_requisicoes"]');

        if (!formFiltros) return;

        // Limpar filtros
        const btnLimpar = formFiltros.querySelector('a[href*="listar_requisicoes"]:not([href*="?"])');
        if (btnLimpar) {
            btnLimpar.addEventListener('click', function (e) {
                e.preventDefault();
                formFiltros.reset();
                window.location.href = btnLimpar.getAttribute('href');
            });
        }
    }

    // ========================================
    // ✅ NOVO: Projeção de Estoque Expansível
    // ========================================
    function inicializarProjecaoToggle() {
        const botoes = document.querySelectorAll('.btn-toggle-projecao');
        console.log('[PROJECAO] Botões encontrados:', botoes.length);

        botoes.forEach(botao => {
            botao.addEventListener('click', function (e) {
                e.stopPropagation(); // Evitar propagação

                const linha = this.closest('tr.linha-produto');  // ✅ MUDOU: linha-produto
                const linhaId = linha.dataset.linhaId;  // ✅ MUDOU: linhaId
                const projecaoRow = document.getElementById(`projecao-${linhaId}`);
                const icone = this.querySelector('i');

                console.log('[PROJECAO] Linha ID:', linhaId);

                if (!projecaoRow) {
                    console.error('[PROJECAO] Row não encontrada:', `projecao-${linhaId}`);
                    return;
                }

                // Toggle expansão
                if (projecaoRow.classList.contains('show')) {
                    // Colapsar
                    projecaoRow.classList.remove('show');
                    icone.classList.remove('fa-chevron-down');
                    icone.classList.add('fa-chevron-right');
                } else {
                    // Expandir
                    projecaoRow.classList.add('show');
                    icone.classList.remove('fa-chevron-right');
                    icone.classList.add('fa-chevron-down');

                    // Carregar projeção se ainda não carregou
                    const conteudo = projecaoRow.querySelector('.projecao-content');
                    if (!conteudo.hasAttribute('data-loaded')) {
                        carregarProjecao(linhaId, conteudo);  // ✅ MUDOU: passa linhaId
                    }
                }
            });
        });
    }

    // ========================================
    // Carregamento de Projeção via AJAX
    // ========================================
    function carregarProjecao(linhaId, container) {
        // ✅ CORRIGIDO: Buscar spinner no elemento pai correto
        const wrapperDiv = container.parentElement;
        const spinner = wrapperDiv.querySelector('.loading-spinner');

        console.log('[PROJECAO] Carregando para linha ID:', linhaId);
        if (spinner) spinner.style.display = 'inline-block';

        fetch(`/manufatura/api/requisicoes-compras/${linhaId}/projecao`)
            .then(response => {
                console.log('[PROJECAO] Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('[PROJECAO] Dados recebidos:', data);
                if (!data.sucesso) {
                    throw new Error(data.erro || 'Erro desconhecido');
                }

                renderizarProjecao(data, container);
                container.setAttribute('data-loaded', 'true');
            })
            .catch(error => {
                console.error('[PROJECAO] Erro ao carregar:', error);
                container.innerHTML = `
                    <div class="alert alert-danger mb-0">
                        <i class="fas fa-exclamation-triangle"></i>
                        Erro ao carregar projeção: ${error.message}
                    </div>
                `;
            })
            .finally(() => {
                if (spinner) spinner.style.display = 'none';
            });
    }

    // ========================================
    // Renderização de Projeção
    // ========================================
    function renderizarProjecao(data, container) {
        const html = `
            ${renderizarTabelaProjecao(data.projecao_diaria, data.data_centro)}

            ${data.pedidos_vinculados.length > 0 ? renderizarPedidosVinculados(data.pedidos_vinculados) : ''}

            ${data.produtos_consumidores.length > 0 ? renderizarProdutosConsumidores(data.produtos_consumidores) : ''}
        `;

        container.innerHTML = html;
    }

    function renderizarTabelaProjecao(projecao, dataCentro) {
        if (!projecao || projecao.length === 0) {
            return '<p class="text-muted">Sem movimentações projetadas no período</p>';
        }

        // ✅ Tabela transposta - Sempre 15 colunas (-D7 a +D7)
        let html = `
            <div class="table-responsive mb-3">
                <table class="table table-sm table-bordered" style="font-size: 0.85rem;">
                    <thead class="table-secondary">
                        <tr>
                            <th style="min-width: 120px; white-space: nowrap;">Métrica</th>
        `;

        // Cabeçalho: Datas (sempre 15 colunas)
        projecao.forEach(dia => {
            const ehCentro = dia.data === dataCentro;
            const dataFormatada = formatarDataISO(dia.data);
            const [d, m] = dataFormatada.split('/');

            html += `
                <th class="text-center ${ehCentro ? 'table-primary' : ''}" style="min-width: 85px; white-space: nowrap;">
                    <div><strong>${d}/${m}</strong></div>
                    ${ehCentro ? '<small class="badge bg-primary">D-Nec</small>' : ''}
                </th>
            `;
        });

        html += `
                        </tr>
                    </thead>
                    <tbody>
        `;

        // Linha 1: Estoque Inicial
        html += '<tr><td class="fw-bold">Est. Inicial</td>';
        projecao.forEach(dia => {
            const ehCentro = dia.data === dataCentro;
            html += `<td class="text-end ${ehCentro ? 'table-primary' : ''}">${formatarNumero(dia.estoque_inicial)}</td>`;
        });
        html += '</tr>';

        // Linha 2: Entradas
        html += '<tr><td class="fw-bold text-success"><i class="fas fa-arrow-down"></i> Entradas</td>';
        projecao.forEach(dia => {
            const ehCentro = dia.data === dataCentro;
            const temEntrada = dia.entradas > 0;
            html += `<td class="text-end ${ehCentro ? 'table-primary' : ''} ${temEntrada ? 'text-success fw-bold' : 'text-muted'}">
                ${temEntrada ? '+' + formatarNumero(dia.entradas) : '-'}
            </td>`;
        });
        html += '</tr>';

        // Linha 3: Consumo
        html += '<tr><td class="fw-bold text-danger"><i class="fas fa-arrow-up"></i> Consumo</td>';
        projecao.forEach(dia => {
            const ehCentro = dia.data === dataCentro;
            const temSaida = dia.saidas > 0;
            html += `<td class="text-end ${ehCentro ? 'table-primary' : ''} ${temSaida ? 'text-danger fw-bold' : 'text-muted'}">
                ${temSaida ? '-' + formatarNumero(dia.saidas) : '-'}
            </td>`;
        });
        html += '</tr>';

        // Linha 4: Estoque Final
        html += '<tr class="table-light"><td class="fw-bold">Est. Final</td>';
        projecao.forEach(dia => {
            const ehCentro = dia.data === dataCentro;
            const estoqueNegativo = dia.estoque_final < 0;
            html += `<td class="text-end fw-bold ${ehCentro ? 'table-primary' : ''} ${estoqueNegativo ? 'bg-danger text-white' : ''}">
                ${formatarNumero(dia.estoque_final)}
                ${estoqueNegativo ? ' <i class="fas fa-exclamation-triangle"></i>' : ''}
            </td>`;
        });
        html += '</tr>';

        html += `
                    </tbody>
                </table>
            </div>
        `;

        return html;
    }

    function renderizarPedidosVinculados(pedidos) {
        let html = `
            <div class="card mb-3">
                <div class="card-header bg-info">
                    <h6 class="mb-0"><i class="fas fa-link"></i> Pedidos de Compra Vinculados</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Pedido</th>
                                    <th>Fornecedor</th>
                                    <th class="text-end">Qtd Alocada</th>
                                    <th class="text-end">Qtd Aberta</th>
                                    <th>Status</th>
                                    <th>Data Previsão</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        pedidos.forEach(pedido => {
            const percentual = pedido.percentual_atendido;
            const corStatus = pedido.status === 'purchase' ? 'success' : 'secondary';

            html += `
                <tr>
                    <td><strong>${pedido.num_pedido}</strong></td>
                    <td>${pedido.fornecedor || '-'}</td>
                    <td class="text-end">${formatarNumero(pedido.qtd_alocada)}</td>
                    <td class="text-end">${formatarNumero(pedido.qtd_aberta)}</td>
                    <td>
                        <span class="badge bg-${corStatus}">${pedido.status}</span>
                        <small class="text-muted">(${percentual}%)</small>
                    </td>
                    <td>${pedido.data_previsao ? formatarDataISO(pedido.data_previsao) : '-'}</td>
                </tr>
            `;
        });

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        return html;
    }

    function renderizarProdutosConsumidores(produtos) {
        let html = `
            <div class="card">
                <div class="card-header bg-warning text-dark">
                    <h6 class="mb-0"><i class="fas fa-industry"></i> Produtos Programados que Consomem</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Produto Programado</th>
                                    <th class="text-end">Qtd Programada</th>
                                    <th>Data Programação</th>
                                    <th class="text-end">Consumo Previsto</th>
                                    <th>Via Intermediário</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        produtos.forEach(prod => {
            html += `
                <tr>
                    <td>
                        <strong>${prod.nome_produto_programado}</strong>
                        <br><small class="text-muted">${prod.cod_produto_programado}</small>
                    </td>
                    <td class="text-end">${formatarNumero(prod.qtd_programada)}</td>
                    <td>${formatarDataISO(prod.data_programacao)}</td>
                    <td class="text-end text-danger"><strong>${formatarNumero(prod.qtd_consumo_previsto)}</strong></td>
                    <td>
                        ${prod.via_intermediario ? `
                            <span class="badge bg-secondary" title="Produto intermediário">
                                ${prod.nome_intermediario}
                            </span>
                            ${prod.caminho_hierarquia && prod.caminho_hierarquia.length > 0 ? `
                                <br><small class="text-muted">${prod.caminho_hierarquia.join(' → ')}</small>
                            ` : ''}
                        ` : '-'}
                    </td>
                </tr>
            `;
        });

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        return html;
    }

    // ========================================
    // Helpers
    // ========================================
    function formatarNumero(numero, casasDecimais = 2) {
        if (typeof numero === 'string') {
            numero = parseFloat(numero);
        }

        if (isNaN(numero) || numero === null || numero === undefined) return '-';

        // ✅ Se for inteiro, não mostrar casas decimais
        const ehInteiro = numero % 1 === 0;

        return numero.toLocaleString('pt-BR', {
            minimumFractionDigits: ehInteiro ? 0 : casasDecimais,
            maximumFractionDigits: casasDecimais
        });
    }

    function formatarData(data) {
        if (!data) return '-';

        const d = new Date(data);

        if (isNaN(d.getTime())) return '-';

        return d.toLocaleDateString('pt-BR');
    }

    function formatarDataISO(dataISO) {
        if (!dataISO) return '-';

        const partes = dataISO.split('-');
        if (partes.length !== 3) return dataISO;

        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    function formatarDataHora(data) {
        if (!data) return '-';

        const d = new Date(data);

        if (isNaN(d.getTime())) return '-';

        return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR');
    }

    // ========================================
    // Exportar funções globais (se necessário)
    // ========================================
    window.RequisicoesCompras = {
        formatarNumero: formatarNumero,
        formatarData: formatarData,
        formatarDataHora: formatarDataHora,
        formatarDataISO: formatarDataISO
    };

})();
