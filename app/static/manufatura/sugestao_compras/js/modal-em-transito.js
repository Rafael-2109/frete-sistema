/**
 * modal-em-transito.js - Modal de detalhamento Em Transito
 *
 * Mostra POs e Requisicoes em transito para um produto.
 * Destaca POs/Requisicoes atrasados (previsao/data_solicitada < hoje).
 */

function abrirModalEmTransito(codProduto) {
    const modal = new bootstrap.Modal(document.getElementById('modalEmTransito'));
    const loading = document.getElementById('et-loading');
    const conteudo = document.getElementById('et-conteudo');

    // Buscar nome do produto nos dados ja carregados
    const prod = dadosSugestoes.find(s => s.cod_produto === codProduto);
    const nomeProduto = prod ? prod.nome_produto : '';
    document.getElementById('et-produto-info').textContent =
        codProduto + (nomeProduto ? ' - ' + nomeProduto : '');

    loading.classList.remove('d-none');
    conteudo.classList.add('d-none');
    modal.show();

    fetch('/manufatura/sugestao-compras/api/em-transito?cod_produto=' + encodeURIComponent(codProduto))
        .then(res => res.json())
        .then(data => {
            loading.classList.add('d-none');

            if (!data.sucesso) {
                toastr.error(data.erro || 'Erro ao carregar dados de transito');
                return;
            }

            renderizarEmTransito(data);
            conteudo.classList.remove('d-none');
        })
        .catch(err => {
            loading.classList.add('d-none');
            toastr.error('Erro de conexao: ' + err.message);
        });
}

function renderizarEmTransito(data) {
    const totais = data.totais;

    // Cards resumo
    document.getElementById('et-total-pedidos').textContent = totais.total_pedidos;
    const saldoPedidosEl = document.getElementById('et-saldo-pedidos');
    saldoPedidosEl.textContent = formatarNumero(totais.saldo_pedidos, 0);

    document.getElementById('et-total-requisicoes').textContent = totais.total_requisicoes;
    const saldoReqEl = document.getElementById('et-saldo-requisicoes');
    saldoReqEl.textContent = formatarNumero(totais.saldo_requisicoes, 0);

    document.getElementById('et-total-transito').textContent = formatarNumero(totais.total_em_transito, 0);

    // Indicadores de atrasados nos cards
    const pedAtrasadosEl = document.getElementById('et-pedidos-atrasados');
    if (totais.pedidos_atrasados > 0) {
        pedAtrasadosEl.textContent = totais.pedidos_atrasados + ' atrasado(s)';
        pedAtrasadosEl.classList.remove('d-none');
    } else {
        pedAtrasadosEl.classList.add('d-none');
    }

    const reqAtrasadasEl = document.getElementById('et-requisicoes-atrasadas');
    if (totais.requisicoes_atrasadas > 0) {
        reqAtrasadasEl.textContent = totais.requisicoes_atrasadas + ' atrasada(s)';
        reqAtrasadasEl.classList.remove('d-none');
    } else {
        reqAtrasadasEl.classList.add('d-none');
    }

    // Tabela Pedidos
    const pedidosBody = document.getElementById('et-pedidos-body');
    if (data.pedidos.length === 0) {
        pedidosBody.innerHTML = '<tr><td colspan="7" class="sc-alerta-vazio"><i class="fas fa-info-circle me-1"></i> Nenhum pedido de compra em transito</td></tr>';
    } else {
        pedidosBody.innerHTML = data.pedidos.map(p => {
            const statusBadge = p.status === 'purchase'
                ? '<span class="sc-badge sc-badge-ok">Confirmado</span>'
                : '<span class="sc-badge sc-badge-mp">' + p.status + '</span>';

            // Previsao: atrasado, sem previsao, ou normal
            let previsaoHtml;
            if (p.sem_previsao) {
                previsaoHtml = '<span class="text-muted">Sem previsao</span>';
            } else if (p.atrasado) {
                previsaoHtml = '<span class="sc-data-atrasada">' + formatarData(p.previsao) + '</span> <span class="sc-badge sc-badge-atrasado">ATRASADO</span>';
            } else {
                previsaoHtml = formatarData(p.previsao);
            }

            const rowClass = p.atrasado ? 'sc-row-ruptura' : '';

            return `<tr class="${rowClass}">
                <td><span class="sc-produto-cod">${p.num_pedido}</span></td>
                <td><span class="sc-produto-nome" title="${p.fornecedor}" style="max-width:200px;display:inline-block">${p.fornecedor}</span></td>
                <td class="text-end">${formatarNumero(p.qtd_pedida, 0)}</td>
                <td class="text-end">${formatarNumero(p.qtd_recebida, 0)}</td>
                <td class="text-end fw-bold">${formatarNumero(p.saldo, 0)}</td>
                <td class="text-center">${statusBadge}</td>
                <td class="text-center">${previsaoHtml}</td>
            </tr>`;
        }).join('');
    }

    // Tabela Requisicoes
    const reqBody = document.getElementById('et-requisicoes-body');
    if (data.requisicoes.length === 0) {
        reqBody.innerHTML = '<tr><td colspan="6" class="sc-alerta-vazio"><i class="fas fa-info-circle me-1"></i> Nenhuma requisicao em transito</td></tr>';
    } else {
        reqBody.innerHTML = data.requisicoes.map(r => {
            // Data solicitada: atrasada ou normal
            let dataSolHtml;
            if (r.atrasada) {
                dataSolHtml = '<span class="sc-data-atrasada">' + formatarData(r.data_solicitada) + '</span> <span class="sc-badge sc-badge-atrasado">ATRASADA</span>';
            } else {
                dataSolHtml = formatarData(r.data_solicitada);
            }

            const rowClass = r.atrasada ? 'sc-row-ruptura' : '';

            return `<tr class="${rowClass}">
                <td><span class="sc-produto-cod">${r.num_requisicao}</span></td>
                <td class="text-end">${formatarNumero(r.qtd_requisitada, 0)}</td>
                <td class="text-end">${formatarNumero(r.qtd_alocada, 0)}</td>
                <td class="text-end fw-bold">${formatarNumero(r.saldo, 0)}</td>
                <td class="text-center"><span class="sc-badge sc-badge-mp">${r.status}</span></td>
                <td class="text-center">${dataSolHtml}</td>
            </tr>`;
        }).join('');
    }
}
