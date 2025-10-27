// ==================================================
// MODAL DE PROJEÇÃO DE ESTOQUE - COM GRÁFICO
// ==================================================

let chartProjecaoInstance = null;

/**
 * Abre o modal de projeção de estoque para um produto específico
 * @param {string} codProduto - Código do produto
 */
function verProjecao(codProduto) {
    const produto = dadosCompletos.find(p => p.cod_produto === codProduto);

    if (!produto) {
        Swal.fire('Erro', 'Produto não encontrado', 'error');
        return;
    }

    // Validar se projeção existe e tem dados
    if (!produto.projecao || !Array.isArray(produto.projecao) || produto.projecao.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'Dados não disponíveis',
            text: 'A projeção de estoque para este produto ainda não foi carregada ou não está disponível.',
            confirmButtonText: 'OK'
        });
        return;
    }

    // Atualizar info do produto no modal
    $('#produto-info-modal').text(`${produto.cod_produto} - ${produto.nome_produto}`);

    // Mostrar modal
    $('#modalProjecao').modal('show');

    // Renderizar conteúdo
    try {
        renderizarIndicadores(produto);
        renderizarGrafico(produto);
        renderizarTabelaProjecao(produto);
    } catch (error) {
        console.error('Erro ao renderizar projeção:', error);
        Swal.fire('Erro', 'Ocorreu um erro ao carregar os dados de projeção', 'error');
    }
}

/**
 * Renderiza os indicadores resumo
 */
function renderizarIndicadores(produto) {
    if (!produto.projecao || produto.projecao.length === 0) {
        console.error('Projeção vazia em renderizarIndicadores');
        return;
    }

    const projecao = produto.projecao;

    // Estoque atual (D0)
    const estoqueAtual = projecao[0]?.saldo_inicial || 0;
    $('#ind-estoque-atual').text(formatarNumero(estoqueAtual));

    // Menor saldo nos próximos 60 dias
    const menorSaldo = Math.min(...projecao.map(p => p.saldo_final || 0));
    $('#ind-menor-saldo').text(formatarNumero(menorSaldo));

    // Dias até ruptura (primeiro dia com saldo < 0)
    const diaRuptura = projecao.findIndex(p => p.saldo_final < 0);
    if (diaRuptura >= 0) {
        $('#ind-dias-ruptura').text(`D${diaRuptura}`);
        $('#ind-dias-ruptura').parent().parent().removeClass('border-warning').addClass('border-danger');
    } else {
        $('#ind-dias-ruptura').text('Sem ruptura');
        $('#ind-dias-ruptura').parent().parent().removeClass('border-danger').addClass('border-success');
    }

    // Saldo final (D60)
    const saldoFinal = projecao[projecao.length - 1]?.saldo_final || 0;
    $('#ind-saldo-final').text(formatarNumero(saldoFinal));

    $('#indicadores-projecao').removeClass('d-none');
}

/**
 * Renderiza o gráfico de projeção com Chart.js
 */
function renderizarGrafico(produto) {
    if (!produto.projecao || produto.projecao.length === 0) {
        console.error('Projeção vazia em renderizarGrafico');
        return;
    }

    const projecao = produto.projecao;

    // Adicionar ponto inicial (antes de D0) para mostrar estoque antes das movimentações
    const estoqueInicial = projecao[0]?.saldo_inicial || 0;

    // Preparar dados para o gráfico com ponto inicial
    const labels = ['Inicial', ...projecao.map(p => `D${p.dia || 0}`)];
    const saldoFinalData = [estoqueInicial, ...projecao.map(p => p.saldo_final || 0)];
    const saidaData = [0, ...projecao.map(p => -Math.abs(p.saida || 0))]; // Negativo para visualização
    const entradaData = [0, ...projecao.map(p => p.entrada || 0)];

    // Destruir gráfico anterior se existir
    if (chartProjecaoInstance) {
        chartProjecaoInstance.destroy();
    }

    const ctx = document.getElementById('chartProjecao').getContext('2d');

    chartProjecaoInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Saldo Final',
                    data: saldoFinalData,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    stepped: 'middle', // Linha muda no MEIO do intervalo
                    pointRadius: 0,
                    pointHoverRadius: 5
                },
                {
                    label: 'Saídas',
                    data: saidaData,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 1.5,
                    fill: true,
                    stepped: 'middle', // Linha muda no MEIO do intervalo
                    pointRadius: 0,
                    pointHoverRadius: 5
                },
                {
                    label: 'Entradas',
                    data: entradaData,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 1.5,
                    fill: true,
                    stepped: 'middle', // Linha muda no MEIO do intervalo
                    pointRadius: 0,
                    pointHoverRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            // Pegar o índice do dia
                            const index = tooltipItems[0].dataIndex;

                            // Se for o ponto inicial (index 0)
                            if (index === 0) {
                                return 'Estoque Inicial';
                            }

                            // Para os demais pontos (D0, D1, D2...)
                            const diaInfo = projecao[index - 1]; // -1 porque adicionamos o ponto inicial

                            if (diaInfo && diaInfo.data) {
                                const data = new Date(diaInfo.data);
                                const dia = String(data.getDate()).padStart(2, '0');
                                const mes = String(data.getMonth() + 1).padStart(2, '0');
                                return `D${diaInfo.dia} - ${dia}/${mes}`;
                            }
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += formatarNumero(Math.abs(context.parsed.y));
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Dias'
                    },
                    grid: {
                        display: true,
                        drawOnChartArea: true,
                        drawTicks: true,
                        color: 'rgba(0, 0, 0, 0.05)', // Grid sutil
                        lineWidth: 1
                    },
                    ticks: {
                        // Mostrar labels: Inicial, D0, D7, D14, D21, etc.
                        callback: function(value, index) {
                            // Sempre mostrar o ponto inicial
                            if (index === 0) {
                                return this.getLabelForValue(value);
                            }
                            // Mostrar D0, D7, D14, D21... (a cada 7 dias após o inicial)
                            if ((index - 1) % 7 === 0 || index === this.ticks.length - 1) {
                                return this.getLabelForValue(value);
                            }
                            return '';
                        },
                        autoSkip: false, // Não pular nenhum tick (cada dia tem seu espaço)
                        maxRotation: 0,
                        minRotation: 0
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Quantidade'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatarNumero(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Renderiza a tabela de projeção dentro do modal
 * @param {object} produto - Objeto com dados do produto e projeção
 */
function renderizarTabelaProjecao(produto) {
    if (!produto.projecao || produto.projecao.length === 0) {
        console.error('Projeção vazia em renderizarTabelaProjecao');
        $('#conteudo-projecao').html('<div class="alert alert-warning">Nenhum dado de projeção disponível</div>');
        return;
    }

    let html = `
        <table class="table table-sm table-bordered table-hover mb-0">
            <thead class="table-light sticky-top">
                <tr>
                    <th>Dia</th>
                    <th>Data</th>
                    <th class="text-end">Saldo Inicial</th>
                    <th class="text-end">Saída</th>
                    <th class="text-end">Entrada</th>
                    <th class="text-end">Saldo Final</th>
                </tr>
            </thead>
            <tbody>`;

    produto.projecao.forEach(item => {
        const cls = item.saldo_final < 0 ? 'table-danger' : item.saldo_final === 0 ? 'table-warning' : '';

        html += `
            <tr class="${cls}">
                <td><strong>D${item.dia}</strong></td>
                <td>${new Date(item.data).toLocaleDateString('pt-BR')}</td>
                <td class="text-end">${formatarNumero(item.saldo_inicial)}</td>
                <td class="text-end text-danger">${formatarNumero(item.saida)}</td>
                <td class="text-end text-success">${formatarNumero(item.entrada)}</td>
                <td class="text-end fw-bold">${formatarNumero(item.saldo_final)}</td>
            </tr>`;
    });

    html += `
            </tbody>
        </table>`;

    $('#conteudo-projecao').html(html);
}
