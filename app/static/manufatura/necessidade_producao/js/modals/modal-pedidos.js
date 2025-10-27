// ==================================================
// MODAL DE PEDIDOS/SEPARAÇÕES
// ==================================================

/**
 * Abre o modal de pedidos para um produto específico
 * @param {string} codProduto - Código do produto
 */
function verPedidos(codProduto) {
    const produto = dadosCompletos.find(p => p.cod_produto === codProduto);

    if (!produto) {
        Swal.fire('Erro', 'Produto não encontrado', 'error');
        return;
    }

    // Atualizar info do produto
    $('#produto-info-pedidos').text(`${produto.cod_produto} - ${produto.nome_produto}`);

    // Mostrar modal e loading
    $('#modalPedidos').modal('show');
    $('#loading-pedidos').removeClass('d-none');
    $('#resumo-pedidos, #accordion-pedidos, #msg-vazio-pedidos').addClass('d-none');

    // Buscar separações via AJAX
    $.ajax({
        url: '/manufatura/api/necessidade-producao/separacoes',
        data: { cod_produto: codProduto },
        success: function(data) {
            $('#loading-pedidos').addClass('d-none');
            renderizarPedidos(data, produto);
        },
        error: function() {
            $('#loading-pedidos').addClass('d-none');
            Swal.fire('Erro', 'Erro ao carregar pedidos', 'error');
        }
    });
}

/**
 * Renderiza os pedidos agrupados por dia
 */
function renderizarPedidos(data, produto) {
    if (!data.separacoes || data.separacoes.length === 0) {
        $('#msg-vazio-pedidos').removeClass('d-none');
        return;
    }

    // Mostrar resumo
    $('#total-sem-separacao').text(formatarNumero(data.total_sem_separacao || 0));
    $('#total-separado').text(formatarNumero(data.total_separado || 0));
    $('#total-pedidos').text(data.separacoes.length);
    $('#total-dias').text(Object.keys(data.por_dia || {}).length);
    $('#resumo-pedidos').removeClass('d-none');

    // Renderizar accordion por dia
    let html = '';
    const diasOrdenados = Object.keys(data.por_dia).sort();

    diasOrdenados.forEach((dia, index) => {
        const dadosDia = data.por_dia[dia];
        const diaFormatado = new Date(dia).toLocaleDateString('pt-BR');
        const isFirst = index === 0;

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading-dia-${index}">
                    <button class="accordion-button ${!isFirst ? 'collapsed' : ''}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#collapse-dia-${index}">
                        <div class="d-flex justify-content-between w-100 me-3">
                            <div>
                                <strong>${diaFormatado}</strong>
                                <span class="badge bg-primary ms-2">${dadosDia.separacoes.length} pedidos</span>
                            </div>
                            <div class="text-end">
                                <small class="text-muted">
                                    Est.Inicial: <strong>${formatarNumero(dadosDia.estoque_inicial)}</strong> |
                                    Saídas: <strong class="text-danger">${formatarNumero(dadosDia.saidas)}</strong> |
                                    Entradas: <strong class="text-success">${formatarNumero(dadosDia.entradas)}</strong> |
                                    Saldo: <strong>${formatarNumero(dadosDia.saldo_final)}</strong>
                                </small>
                            </div>
                        </div>
                    </button>
                </h2>
                <div id="collapse-dia-${index}" class="accordion-collapse collapse ${isFirst ? 'show' : ''}"
                     data-bs-parent="#accordion-pedidos">
                    <div class="accordion-body p-0">
                        <table class="table table-sm table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Cliente</th>
                                    <th class="text-center">CNPJ</th>
                                    <th class="text-end">Qtd</th>
                                    <th class="text-center">Expedição</th>
                                    <th class="text-center">Agendamento</th>
                                    <th class="text-center">Status</th>
                                </tr>
                            </thead>
                            <tbody>`;

        dadosDia.separacoes.forEach(sep => {
            const statusClass = getStatusClass(sep.status);
            html += `
                <tr class="cursor-pointer" onclick="verDetalhesSeparacao('${sep.separacao_lote_id}')">
                    <td>
                        <div class="text-truncate" style="max-width: 250px;" title="${sep.raz_social_red || ''}">
                            ${sep.raz_social_red || '-'}
                        </div>
                        <small class="text-muted">${sep.nome_cidade || ''} - ${sep.cod_uf || ''}</small>
                    </td>
                    <td class="text-center"><small>${sep.cnpj_cpf || '-'}</small></td>
                    <td class="text-end"><strong>${formatarNumero(sep.qtd_saldo || 0)}</strong></td>
                    <td class="text-center"><small>${sep.expedicao ? new Date(sep.expedicao).toLocaleDateString('pt-BR') : '-'}</small></td>
                    <td class="text-center"><small>${sep.agendamento ? new Date(sep.agendamento).toLocaleDateString('pt-BR') : '-'}</small></td>
                    <td class="text-center">
                        <span class="badge ${statusClass}">${sep.status || 'ABERTO'}</span>
                    </td>
                </tr>`;
        });

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>`;
    });

    $('#accordion-pedidos').html(html).removeClass('d-none');
}

/**
 * Retorna a classe CSS do badge de status
 */
function getStatusClass(status) {
    const statusMap = {
        'ABERTO': 'bg-info',
        'COTADO': 'bg-warning',
        'EMBARCADO': 'bg-primary',
        'FATURADO': 'bg-success',
        'NF no CD': 'bg-secondary',
        'PREVISAO': 'bg-light text-dark'
    };
    return statusMap[status] || 'bg-secondary';
}

/**
 * Abre modal com detalhes da separação
 */
function verDetalhesSeparacao(separacaoLoteId) {
    // Buscar detalhes via AJAX
    $.ajax({
        url: '/manufatura/api/necessidade-producao/separacao-detalhes',
        data: { separacao_lote_id: separacaoLoteId },
        success: function(data) {
            renderizarDetalhesSeparacao(data);
            $('#modalDetalhesSeparacao').modal('show');
        },
        error: function() {
            Swal.fire('Erro', 'Erro ao carregar detalhes', 'error');
        }
    });
}

/**
 * Renderiza detalhes da separação
 */
function renderizarDetalhesSeparacao(data) {
    let html = `
        <div class="row g-3">
            <div class="col-md-6">
                <strong>Lote de Separação:</strong><br>
                <code>${data.separacao_lote_id}</code>
            </div>
            <div class="col-md-6">
                <strong>Status:</strong><br>
                <span class="badge ${getStatusClass(data.status)}">${data.status || 'ABERTO'}</span>
            </div>
        </div>
        <hr>
        <div class="row g-3">
            <div class="col-md-12">
                <strong>Cliente:</strong><br>
                ${data.raz_social_red || '-'}<br>
                <small class="text-muted">CNPJ: ${data.cnpj_cpf || '-'}</small>
            </div>
        </div>
        <hr>
        <div class="row g-3">
            <div class="col-md-4">
                <strong>Expedição:</strong><br>
                ${data.expedicao ? new Date(data.expedicao).toLocaleDateString('pt-BR') : '-'}
            </div>
            <div class="col-md-4">
                <strong>Agendamento:</strong><br>
                ${data.agendamento ? new Date(data.agendamento).toLocaleDateString('pt-BR') : '-'}
            </div>
            <div class="col-md-4">
                <strong>Protocolo:</strong><br>
                ${data.protocolo || '-'}
            </div>
        </div>
        <hr>
        <h6>Itens da Separação:</h6>
        <table class="table table-sm table-bordered">
            <thead class="table-light">
                <tr>
                    <th>Produto</th>
                    <th class="text-end">Quantidade</th>
                    <th class="text-end">Valor</th>
                    <th class="text-end">Peso</th>
                </tr>
            </thead>
            <tbody>`;

    (data.itens || [data]).forEach(item => {
        html += `
            <tr>
                <td>
                    <strong>${item.cod_produto}</strong><br>
                    <small>${item.nome_produto || ''}</small>
                </td>
                <td class="text-end">${formatarNumero(item.qtd_saldo || 0)}</td>
                <td class="text-end">R$ ${formatarNumero(item.valor_saldo || 0)}</td>
                <td class="text-end">${formatarNumero(item.peso || 0)} kg</td>
            </tr>`;
    });

    html += `
            </tbody>
        </table>`;

    if (data.observ_ped_1) {
        html += `
            <hr>
            <strong>Observações:</strong><br>
            <p class="text-muted">${data.observ_ped_1}</p>`;
    }

    $('#conteudo-detalhes-separacao').html(html);
}
