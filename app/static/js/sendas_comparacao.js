/**
 * JavaScript para gerenciar comparação e agendamento Sendas - Etapa 2
 * Suporta os 3 fluxos: Lote, Separação e NF
 */

// ========================================
// FUNÇÕES AUXILIARES
// ========================================

/**
 * Obtém o token CSRF do meta tag ou cookie
 */
function getCSRFToken() {
    // Primeiro tentar do meta tag
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) {
        return token.getAttribute('content');
    }

    // Se não encontrar, tentar do cookie
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];

    return cookieValue || '';
}

// ========================================
// FLUXO 2 - SEPARAÇÃO (Individual)
// ========================================

/**
 * Abre modal de comparação para separação
 * @param {string} separacaoLoteId - ID da separação
 * @param {string} cnpj - CNPJ do cliente
 * @param {string} pedidoCliente - Pedido do cliente
 * @param {string} codProduto - Código do produto
 * @param {number} quantidade - Quantidade solicitada
 */
function abrirModalComparacaoSeparacao(separacaoLoteId, cnpj, pedidoCliente, codProduto, quantidade, nomeProduto) {
    // Preencher dados da solicitação
    $('#sep-cnpj').text(cnpj);
    $('#sep-pedido').text(pedidoCliente);
    $('#sep-produto').text(`${codProduto} - ${nomeProduto || ''}`);
    $('#sep-quantidade').text(quantidade);
    $('#sep-lote-id').text(separacaoLoteId);

    // Definir data de agendamento padrão (hoje + 1 dia útil)
    const dataAgenda = new Date();
    dataAgenda.setDate(dataAgenda.getDate() + 1);
    $('#sep-data-agendamento').val(dataAgenda.toISOString().split('T')[0]);

    // Armazenar dados no modal para uso posterior
    $('#modalComparacaoSeparacao').data('solicitacao', {
        separacao_lote_id: separacaoLoteId,
        cnpj: cnpj,
        pedido_cliente: pedidoCliente,
        cod_produto: codProduto,
        quantidade: quantidade
    });

    // Limpar resultados anteriores
    $('#resultado-comparacao-sep').html('');
    $('#card-alternativas-sep').hide();
    $('#btn-confirmar-sep').hide();
    $('#btn-comparar-sep').show();

    // Abrir modal
    $('#modalComparacaoSeparacao').modal('show');
}

/**
 * Executa comparação para separação
 */
function compararSeparacao() {
    const solicitacao = $('#modalComparacaoSeparacao').data('solicitacao');
    const dataAgendamento = $('#sep-data-agendamento').val();

    if (!dataAgendamento) {
        alert('Por favor, selecione uma data de agendamento');
        return;
    }

    // Mostrar loading
    $('#btn-comparar-sep').prop('disabled', true).html(
        '<span class="spinner-border spinner-border-sm"></span> Comparando...'
    );

    // Fazer requisição
    $.ajax({
        url: '/portal/sendas/solicitar/separacao/comparar',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        data: JSON.stringify({
            separacao_lote_id: solicitacao.separacao_lote_id,
            cnpj: solicitacao.cnpj,
            pedido_cliente: solicitacao.pedido_cliente,
            cod_produto: solicitacao.cod_produto,
            quantidade: solicitacao.quantidade,
            data_agendamento: dataAgendamento
        }),
        success: function(resultado) {
            exibirResultadoComparacaoSeparacao(resultado);
        },
        error: function(xhr) {
            const erro = xhr.responseJSON?.erro || 'Erro ao comparar';
            $('#resultado-comparacao-sep').html(
                `<div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> ${erro}
                </div>`
            );
        },
        complete: function() {
            $('#btn-comparar-sep').prop('disabled', false).html(
                '<i class="fas fa-search"></i> Comparar'
            );
        }
    });
}

/**
 * Exibe resultado da comparação de separação
 */
function exibirResultadoComparacaoSeparacao(resultado) {
    let html = '';

    if (resultado.tipo_match === 'exato') {
        // Match exato encontrado
        const disponivel = resultado.disponibilidades[0];
        const suficiente = resultado.quantidade_suficiente;

        html = `
            <div class="alert ${suficiente ? 'alert-success' : 'alert-warning'}">
                <h6>${suficiente ? '✅ Disponibilidade confirmada!' : '⚠️ Disponibilidade parcial'}</h6>
                <div class="mt-2">
                    <strong>Pedido Sendas:</strong> ${disponivel.codigo_pedido_sendas}<br>
                    <strong>Produto:</strong> ${disponivel.descricao}<br>
                    <strong>Disponível:</strong> ${disponivel.saldo_disponivel} ${disponivel.unidade_medida}<br>
                    <strong>Solicitado:</strong> ${resultado.solicitacao.quantidade_solicitada}<br>
                    ${!suficiente ? '<em class="text-danger">Quantidade insuficiente - ajuste a quantidade ou escolha alternativas</em>' : ''}
                </div>
            </div>
        `;

        // Armazenar item para confirmação
        $('#modalComparacaoSeparacao').data('item_confirmado', {
            ...resultado.solicitacao,
            ...disponivel,
            codigo_pedido_sendas: disponivel.codigo_pedido_sendas,
            separacao_lote_id: $('#modalComparacaoSeparacao').data('solicitacao').separacao_lote_id
        });

        if (suficiente) {
            $('#btn-confirmar-sep').show();
        }

    } else if (resultado.tipo_match === 'filial_apenas') {
        // Não encontrou pedido específico, mas tem alternativas
        html = `
            <div class="alert alert-info">
                <h6>ℹ️ Pedido não encontrado</h6>
                <p>${resultado.sugestao || 'Há outros produtos disponíveis nesta filial'}</p>
            </div>
        `;

        // Mostrar alternativas
        mostrarAlternativasSeparacao(resultado.pedidos_alternativos);

    } else {
        // Nenhum match
        html = `
            <div class="alert alert-danger">
                <h6>❌ Nenhuma disponibilidade encontrada</h6>
                <p>${resultado.erro}</p>
            </div>
        `;
    }

    $('#resultado-comparacao-sep').html(html);
}

/**
 * Mostra alternativas disponíveis para separação
 */
function mostrarAlternativasSeparacao(pedidosAlternativos) {
    $('#card-alternativas-sep').show();

    const tabela = $('#tabela-alternativas-sep tbody');
    tabela.empty();

    let contador = 0;
    for (const [pedido, produtos] of Object.entries(pedidosAlternativos)) {
        produtos.forEach(produto => {
            contador++;
            tabela.append(`
                <tr>
                    <td>
                        <input type="checkbox" class="check-alternativa-sep"
                               data-pedido="${pedido}"
                               data-produto='${JSON.stringify(produto)}'>
                    </td>
                    <td>${pedido}</td>
                    <td>${produto.codigo_produto_sendas}</td>
                    <td>${produto.descricao}</td>
                    <td>${produto.saldo_disponivel}</td>
                    <td>${produto.unidade_medida}</td>
                </tr>
            `);
        });
    }

    $('#sugestao-sep').text(`Encontramos ${contador} alternativas disponíveis. Selecione uma para agendar:`);

    // Configurar checkbox "selecionar todos"
    $('#check-all-sep').off('change').on('change', function() {
        $('.check-alternativa-sep').prop('checked', $(this).is(':checked'));
        verificarSelecaoAlternativasSep();
    });

    // Verificar seleção individual
    $('.check-alternativa-sep').off('change').on('change', verificarSelecaoAlternativasSep);
}

function verificarSelecaoAlternativasSep() {
    const selecionados = $('.check-alternativa-sep:checked');
    if (selecionados.length === 1) {
        // Permitir confirmação apenas com 1 selecionado
        const produto = JSON.parse(selecionados.first().data('produto'));
        const solicitacao = $('#modalComparacaoSeparacao').data('solicitacao');

        // IMPORTANTE: Enviar APENAS dados da planilha modelo (o que será agendado)
        $('#modalComparacaoSeparacao').data('item_confirmado', {
            // Identificação e rastreabilidade
            separacao_lote_id: solicitacao.separacao_lote_id,
            tipo_origem: 'separacao',
            documento_origem: solicitacao.separacao_lote_id,

            // Dados da PLANILHA MODELO (o que será efetivamente agendado)
            codigo_pedido_sendas: produto.codigo_pedido_sendas,
            codigo_produto_sendas: produto.codigo_produto_sendas,
            descricao: produto.descricao,
            saldo_disponivel: produto.saldo_disponivel,
            unidade_medida: produto.unidade_medida,

            // Data do agendamento
            data_agendamento: $('#sep-data-agendamento').val(),

            // Quantidade solicitada (respeitando limite da planilha)
            quantidade_solicitada: Math.min(
                solicitacao.quantidade_solicitada || solicitacao.quantidade || produto.saldo_disponivel,
                produto.saldo_disponivel
            )
        });

        $('#btn-confirmar-sep').show();
    } else {
        $('#btn-confirmar-sep').hide();
    }
}

/**
 * Confirma agendamento de separação
 */
function confirmarSeparacao() {
    const itemConfirmado = $('#modalComparacaoSeparacao').data('item_confirmado');

    if (!itemConfirmado) {
        alert('Nenhum item selecionado para confirmação');
        return;
    }

    // Mostrar loading
    $('#btn-confirmar-sep').prop('disabled', true).html(
        '<span class="spinner-border spinner-border-sm"></span> Confirmando...'
    );

    $.ajax({
        url: '/portal/sendas/solicitar/separacao/confirmar',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        data: JSON.stringify({
            itens_confirmados: [itemConfirmado]  // Sempre enviar como array
        }),
        success: function(resultado) {
            if (resultado.sucesso) {
                exibirProtocoloGerado(resultado.protocolo, 'separação');
                $('#modalComparacaoSeparacao').modal('hide');
            } else {
                alert('Erro ao confirmar: ' + resultado.erro);
            }
        },
        error: function(xhr) {
            alert('Erro ao confirmar agendamento');
        },
        complete: function() {
            $('#btn-confirmar-sep').prop('disabled', false).html(
                '<i class="fas fa-check"></i> Confirmar Agendamento'
            );
        }
    });
}

// ========================================
// FLUXO 1 - LOTE (Múltiplos)
// ========================================

/**
 * Abre modal de comparação para lote
 * @param {Array} cnpjsSelecionados - Lista de CNPJs selecionados
 */
function abrirModalComparacaoLote(cnpjsSelecionados) {
    // Mostrar lista de CNPJs
    const listaCnpjs = $('#lista-cnpjs-lote');
    listaCnpjs.empty();

    cnpjsSelecionados.forEach(cnpj => {
        listaCnpjs.append(`
            <div class="badge bg-secondary mb-1 w-100">
                ${cnpj.cnpj} - ${cnpj.cliente || ''}
            </div>
        `);
    });

    // Armazenar dados
    $('#modalComparacaoLote').data('cnpjs', cnpjsSelecionados);

    // Limpar resultados
    $('#resultados-lote').empty();
    $('#resumo-lote').text('Nenhuma comparação realizada ainda');
    $('#btn-confirmar-lote').hide();

    // Abrir modal
    $('#modalComparacaoLote').modal('show');
}

/**
 * Executa comparação para lote
 */
function compararLote() {
    const cnpjsDados = $('#modalComparacaoLote').data('cnpjs');

    if (!cnpjsDados || cnpjsDados.length === 0) {
        alert('Nenhum CNPJ selecionado');
        return;
    }

    // Montar solicitações (exemplo - adaptar conforme necessidade)
    const solicitacoes = [];
    cnpjsDados.forEach(item => {
        // Aqui você deve pegar os dados reais dos pedidos/produtos
        // Este é apenas um exemplo
        if (item.pedidos && item.pedidos.length > 0) {
            item.pedidos.forEach(pedido => {
                solicitacoes.push({
                    cnpj: item.cnpj,
                    pedido_cliente: pedido.pedido_cliente,
                    cod_produto: pedido.cod_produto,
                    quantidade: pedido.quantidade,
                    data_agendamento: pedido.data_agendamento || new Date().toISOString().split('T')[0]
                });
            });
        }
    });

    if (solicitacoes.length === 0) {
        alert('Nenhuma solicitação para comparar');
        return;
    }

    // Mostrar loading
    $('#btn-comparar-lote').prop('disabled', true).html(
        '<span class="spinner-border spinner-border-sm"></span> Comparando...'
    );

    $.ajax({
        url: '/portal/sendas/solicitar/lote/comparar',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        data: JSON.stringify({ solicitacoes: solicitacoes }),
        success: function(resultado) {
            exibirResultadosLote(resultado.resultados_por_cnpj);
        },
        error: function(xhr) {
            alert('Erro ao comparar lote');
        },
        complete: function() {
            $('#btn-comparar-lote').prop('disabled', false).html(
                '<i class="fas fa-search"></i> Comparar Todos'
            );
        }
    });
}

/**
 * Exibe resultados da comparação em lote
 */
function exibirResultadosLote(resultadosPorCnpj) {
    const container = $('#resultados-lote');
    container.empty();

    let totalItens = 0;
    let totalConfirmados = 0;
    const itensParaConfirmar = [];

    // Criar accordion com resultados
    const accordionId = 'accordionLote';
    let accordionHtml = `<div class="accordion" id="${accordionId}">`;

    Object.entries(resultadosPorCnpj).forEach(([cnpj, dados], index) => {
        const collapseId = `collapse${index}`;
        const headerId = `heading${index}`;

        let statusIcon = '⚠️';
        let statusClass = 'warning';
        let itensSucesso = 0;

        // Verificar status dos itens
        dados.itens.forEach(item => {
            totalItens++;
            if (item.sucesso && item.tipo_match === 'exato' && item.quantidade_suficiente) {
                itensSucesso++;
                totalConfirmados++;

                // Adicionar à lista de confirmação
                if (item.disponibilidades && item.disponibilidades.length > 0) {
                    const disp = item.disponibilidades[0];
                    // IMPORTANTE: Enviar APENAS dados da planilha modelo (o que será agendado)
                    itensParaConfirmar.push({
                        // Identificação e rastreabilidade
                        cnpj: cnpj,
                        tipo_origem: 'lote',
                        documento_origem: item.solicitacao.num_pedido || item.solicitacao.pedido_cliente,

                        // Dados da PLANILHA MODELO (o que será efetivamente agendado)
                        codigo_pedido_sendas: disp.codigo_pedido_sendas,
                        codigo_produto_sendas: disp.codigo_produto_sendas,
                        descricao: disp.descricao,
                        saldo_disponivel: disp.saldo_disponivel,
                        unidade_medida: disp.unidade_medida,

                        // Data do agendamento
                        data_agendamento: item.solicitacao.data_agendamento || new Date().toISOString().split('T')[0],

                        // Quantidade solicitada (respeitando limite da planilha)
                        quantidade_solicitada: Math.min(
                            item.solicitacao.quantidade_solicitada || item.solicitacao.quantidade,
                            disp.saldo_disponivel
                        )
                    });
                }
            }
        });

        if (itensSucesso === dados.itens.length) {
            statusIcon = '✅';
            statusClass = 'success';
        } else if (itensSucesso > 0) {
            statusIcon = '⚠️';
            statusClass = 'warning';
        } else {
            statusIcon = '❌';
            statusClass = 'danger';
        }

        accordionHtml += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="${headerId}">
                    <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#${collapseId}">
                        <span class="badge bg-${statusClass} me-2">${statusIcon}</span>
                        ${cnpj} - ${itensSucesso}/${dados.itens.length} itens disponíveis
                    </button>
                </h2>
                <div id="${collapseId}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     data-bs-parent="#${accordionId}">
                    <div class="accordion-body">
        `;

        // Listar itens do CNPJ
        dados.itens.forEach(item => {
            if (item.sucesso && item.tipo_match === 'exato') {
                const disp = item.disponibilidades[0];
                accordionHtml += `
                    <div class="alert alert-${item.quantidade_suficiente ? 'success' : 'warning'} py-2">
                        <strong>Pedido:</strong> ${item.solicitacao.pedido_cliente} |
                        <strong>Produto:</strong> ${disp.descricao} |
                        <strong>Disponível:</strong> ${disp.saldo_disponivel} / ${item.solicitacao.quantidade_solicitada}
                        ${item.quantidade_suficiente ? '<span class="badge bg-success ms-2">OK</span>' : '<span class="badge bg-warning ms-2">Parcial</span>'}
                    </div>
                `;
            } else if (item.tipo_match === 'filial_apenas') {
                accordionHtml += `
                    <div class="alert alert-info py-2">
                        <strong>Pedido:</strong> ${item.solicitacao.pedido_cliente} -
                        <em>Não encontrado, mas há alternativas na filial</em>
                    </div>
                `;
            } else {
                accordionHtml += `
                    <div class="alert alert-danger py-2">
                        <strong>Pedido:</strong> ${item.solicitacao.pedido_cliente || 'N/A'} -
                        <em>${item.erro || 'Sem disponibilidade'}</em>
                    </div>
                `;
            }
        });

        accordionHtml += `
                    </div>
                </div>
            </div>
        `;
    });

    accordionHtml += '</div>';
    container.html(accordionHtml);

    // Atualizar resumo
    $('#resumo-lote').text(
        `Total: ${totalItens} itens analisados | ${totalConfirmados} disponíveis para agendamento`
    );

    // Armazenar itens para confirmação
    if (itensParaConfirmar.length > 0) {
        $('#modalComparacaoLote').data('itens_confirmados', itensParaConfirmar);
        $('#btn-confirmar-lote').show();
    }
}

/**
 * Confirma agendamento em lote
 */
function confirmarLote() {
    const itensConfirmados = $('#modalComparacaoLote').data('itens_confirmados');

    if (!itensConfirmados || itensConfirmados.length === 0) {
        alert('Nenhum item para confirmar');
        return;
    }

    // Mostrar loading
    $('#btn-confirmar-lote').prop('disabled', true).html(
        '<span class="spinner-border spinner-border-sm"></span> Confirmando...'
    );

    $.ajax({
        url: '/portal/sendas/solicitar/lote/confirmar',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        data: JSON.stringify({ itens_confirmados: itensConfirmados }),
        success: function(resultado) {
            if (resultado.sucesso) {
                // Mostrar protocolos gerados
                let mensagem = `${resultado.mensagem}\n\nProtocolos gerados:\n`;
                Object.entries(resultado.protocolos).forEach(([cnpj, protocolo]) => {
                    mensagem += `${cnpj}: ${protocolo}\n`;
                });

                exibirProtocolosLote(resultado.protocolos);
                $('#modalComparacaoLote').modal('hide');
            } else {
                alert('Erro ao confirmar: ' + resultado.erro);
            }
        },
        error: function(xhr) {
            alert('Erro ao confirmar agendamentos');
        },
        complete: function() {
            $('#btn-confirmar-lote').prop('disabled', false).html(
                '<i class="fas fa-check"></i> Confirmar Agendamentos Selecionados'
            );
        }
    });
}

// ========================================
// FLUXO 3 - NF/MONITORAMENTO
// ========================================

/**
 * Abre modal de comparação para NF
 * @param {string} numeroNf - Número da NF
 * @param {string} cnpjCliente - CNPJ do cliente
 */
function abrirModalComparacaoNF(numeroNf, cnpjCliente) {
    // Preencher dados
    $('#nf-numero').text(numeroNf);
    $('#nf-cnpj').text(cnpjCliente);

    // Data padrão
    const dataAgenda = new Date();
    dataAgenda.setDate(dataAgenda.getDate() + 1);
    $('#nf-data-agendamento').val(dataAgenda.toISOString().split('T')[0]);

    // Armazenar dados
    $('#modalComparacaoNF').data('nf_dados', {
        numero_nf: numeroNf,
        cnpj: cnpjCliente
    });

    // Limpar resultados
    $('#resultado-comparacao-nf').empty();
    $('#btn-confirmar-nf').hide();

    // Abrir modal
    $('#modalComparacaoNF').modal('show');
}

/**
 * Executa comparação para NF
 */
function compararNF() {
    const dados = $('#modalComparacaoNF').data('nf_dados');
    const dataAgendamento = $('#nf-data-agendamento').val();

    if (!dataAgendamento) {
        alert('Por favor, selecione uma data de agendamento');
        return;
    }

    // Mostrar loading
    $('#btn-comparar-nf').prop('disabled', true).html(
        '<span class="spinner-border spinner-border-sm"></span> Comparando...'
    );

    $.ajax({
        url: '/portal/sendas/solicitar/nf/comparar',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        data: JSON.stringify({
            numero_nf: dados.numero_nf,
            data_agendamento: dataAgendamento
        }),
        success: function(resultado) {
            exibirResultadoComparacaoNF(resultado);
        },
        error: function(xhr) {
            const erro = xhr.responseJSON?.erro || 'Erro ao comparar';
            $('#resultado-comparacao-nf').html(
                `<div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> ${erro}
                </div>`
            );
        },
        complete: function() {
            $('#btn-comparar-nf').prop('disabled', false).html(
                '<i class="fas fa-search"></i> Comparar'
            );
        }
    });
}

/**
 * Exibe resultado da comparação de NF
 * ✅ CORRIGIDO: Processa estrutura resultados_por_cnpj corretamente
 */
function exibirResultadoComparacaoNF(resultado) {
    let html = '';

    // ✅ ESTRUTURA CORRETA: resultado.resultados_por_cnpj[cnpj]
    if (!resultado.sucesso || !resultado.resultados_por_cnpj) {
        html = `
            <div class="alert alert-danger">
                <h6>❌ Erro na comparação</h6>
                <p>${resultado.erro || 'Erro desconhecido'}</p>
            </div>
        `;
        $('#resultado-comparacao-nf').html(html);
        return;
    }

    // Pegar o primeiro (e único) CNPJ do resultado
    const cnpjs = Object.keys(resultado.resultados_por_cnpj);
    if (cnpjs.length === 0) {
        html = `
            <div class="alert alert-warning">
                <h6>⚠️ Nenhum resultado encontrado</h6>
            </div>
        `;
        $('#resultado-comparacao-nf').html(html);
        return;
    }

    const cnpj = cnpjs[0];
    const dadosCnpj = resultado.resultados_por_cnpj[cnpj];

    // Verificar se há itens
    if (!dadosCnpj.itens || dadosCnpj.itens.length === 0) {
        html = `
            <div class="alert alert-warning">
                <h6>⚠️ Nenhum item encontrado para este CNPJ</h6>
            </div>
        `;
        $('#resultado-comparacao-nf').html(html);
        return;
    }

    // Pegar o primeiro item
    const item = dadosCnpj.itens[0];

    if (item.tipo_match === 'exato' && item.encontrado) {
        const disponivel = item.encontrado;
        const solicitado = item.solicitado;

        html = `
            <div class="alert alert-success">
                <h6>✅ Disponibilidade confirmada!</h6>
                <div class="mt-2">
                    <strong>Pedido:</strong> ${disponivel.codigo_pedido_sendas}<br>
                    <strong>Produto:</strong> ${disponivel.descricao}<br>
                    <strong>Disponível:</strong> ${disponivel.saldo_disponivel} ${disponivel.unidade_medida}
                </div>
            </div>
        `;

        // ✅ CORRIGIDO: Armazenar TODOS os campos necessários para o backend
        $('#modalComparacaoNF').data('item_confirmado', {
            // Identificação e rastreabilidade
            numero_nf: resultado.numero_nf,
            entrega_id: dadosCnpj.entrega_id,
            tipo_origem: 'nf',
            documento_origem: resultado.numero_nf,

            // ✅ Dados do NOSSO sistema (obrigatórios para o backend)
            cnpj: cnpj,
            num_pedido: solicitado.num_pedido,
            cod_produto: solicitado.cod_produto,
            pedido_cliente: solicitado.pedido_cliente,
            nome_produto: disponivel.descricao,

            // Dados da PLANILHA MODELO (para referência)
            codigo_pedido_sendas: disponivel.codigo_pedido_sendas,
            codigo_produto_sendas: disponivel.codigo_produto_sendas,
            saldo_disponivel: disponivel.saldo_disponivel,
            unidade_medida: disponivel.unidade_medida,

            // Data do agendamento
            data_agendamento: $('#nf-data-agendamento').val() || new Date().toISOString().split('T')[0],

            // Quantidade (usando nome esperado pelo backend)
            quantidade: Math.min(
                solicitado.quantidade || disponivel.saldo_disponivel,
                disponivel.saldo_disponivel
            )
        });

        $('#btn-confirmar-nf').show();

    } else {
        html = `
            <div class="alert alert-warning">
                <h6>⚠️ Disponibilidade não encontrada</h6>
                <p>${item.observacao || 'Produto não encontrado na planilha Sendas'}</p>
            </div>
        `;
    }

    $('#resultado-comparacao-nf').html(html);
}

/**
 * Confirma agendamento de NF
 */
function confirmarNF() {
    const itemConfirmado = $('#modalComparacaoNF').data('item_confirmado');

    if (!itemConfirmado) {
        alert('Nenhum item para confirmar');
        return;
    }

    // Mostrar loading
    $('#btn-confirmar-nf').prop('disabled', true).html(
        '<span class="spinner-border spinner-border-sm"></span> Confirmando...'
    );

    $.ajax({
        url: '/portal/sendas/solicitar/nf/confirmar',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        data: JSON.stringify({
            itens_confirmados: [itemConfirmado],  // Sempre enviar como array
            numero_nf: itemConfirmado.numero_nf
        }),
        success: function(resultado) {
            if (resultado.sucesso) {
                exibirProtocoloGerado(resultado.protocolo, 'NF');
                $('#modalComparacaoNF').modal('hide');
            } else {
                alert('Erro ao confirmar: ' + resultado.erro);
            }
        },
        error: function(xhr) {
            alert('Erro ao confirmar agendamento');
        },
        complete: function() {
            $('#btn-confirmar-nf').prop('disabled', false).html(
                '<i class="fas fa-check"></i> Confirmar Agendamento'
            );
        }
    });
}

// ========================================
// FUNÇÕES AUXILIARES
// ========================================

/**
 * Exibe modal com protocolo gerado
 */
function exibirProtocoloGerado(protocolo, tipo) {
    $('#protocolo-gerado').text(protocolo);
    $('#detalhes-protocolo').html(`
        <p class="mb-0">Tipo: <strong>${tipo}</strong></p>
        <p class="mb-0">Data/Hora: <strong>${new Date().toLocaleString('pt-BR')}</strong></p>
    `);
    $('#modalProtocoloGerado').modal('show');
}

/**
 * Exibe múltiplos protocolos (para lote)
 */
function exibirProtocolosLote(protocolos) {
    let detalhes = '<h5>Protocolos Gerados:</h5><ul>';
    Object.entries(protocolos).forEach(([cnpj, protocolo]) => {
        detalhes += `<li><strong>${cnpj}:</strong> ${protocolo}</li>`;
    });
    detalhes += '</ul>';

    $('#protocolo-gerado').text('Múltiplos protocolos');
    $('#detalhes-protocolo').html(detalhes);
    $('#modalProtocoloGerado').modal('show');
}

/**
 * Copia protocolo para clipboard
 */
function copiarProtocolo() {
    const protocolo = $('#protocolo-gerado').text();

    // Criar elemento temporário
    const temp = $('<textarea>');
    $('body').append(temp);
    temp.val(protocolo).select();
    document.execCommand('copy');
    temp.remove();

    // Feedback visual
    const btn = $('button[onclick="copiarProtocolo()"]');
    const textoOriginal = btn.html();
    btn.html('<i class="fas fa-check"></i> Copiado!').addClass('btn-success').removeClass('btn-secondary');
    setTimeout(() => {
        btn.html(textoOriginal).addClass('btn-secondary').removeClass('btn-success');
    }, 2000);
}

// ========================================
// INICIALIZAÇÃO
// ========================================

$(document).ready(function() {
    // Configurar máscaras se necessário

    // Event listeners globais
    console.log('Sendas Comparação JS carregado');
});