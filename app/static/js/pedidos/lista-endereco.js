/**
 * lista-endereco.js — Modal de endereco do pedido
 * Extraido de lista_pedidos.html (linhas 2690-2933)
 */

async function abrirModalEnderecoPedido(numPedido, loteId) {
    try {
        let response, data, fonte;

        // ===== CarVia: endpoint específico =====
        if (loteId && loteId.startsWith('CARVIA-')) {
            response = await fetch('/pedidos/api/endereco-carvia/' + loteId);
            data = await response.json();
            fonte = 'carvia';

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar dados do endereco CarVia');
            }
        } else {
            // ===== Nacom: fluxo original =====
            response = await fetch('/pedidos/api/pedido/' + numPedido + '/endereco-carteira');
            data = await response.json();
            fonte = 'carteira';

            if (!response.ok || !data.success) {
                response = await fetch('/pedidos/api/pedido/' + numPedido + '/endereco-receita');
                data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Erro ao carregar dados do endereco');
                }

                fonte = data.fonte || 'receita';
            }
        }

        if (!document.getElementById('modalEnderecoPedido')) {
            criarModalEnderecoPedido(fonte);
        } else {
            atualizarTituloModal(fonte);
        }

        preencherDadosEnderecoPedido(data.dados, fonte);

        const modalElement = document.getElementById('modalEnderecoPedido');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();

        if (fonte === 'receita' && data.dados.separacao_lote_id && data.dados.nome_cidade) {
            await atualizarCidadeSeparacao(data.dados.separacao_lote_id, data.dados.nome_cidade);
        }

    } catch (error) {
        console.error('Erro ao carregar endereco:', error);
        alert('Erro ao carregar dados do endereco: ' + error.message);
    }
}

async function atualizarCidadeSeparacao(loteId, cidade) {
    try {
        const response = await fetch('/pedidos/api/separacao/' + loteId + '/atualizar-cidade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({ cidade: cidade })
        });

        const data = await response.json();

        if (data.success) {
            console.log('Cidade atualizada: ' + data.atualizados + ' registro(s)');
        } else {
            console.warn('Erro ao atualizar cidade: ' + data.error);
        }
    } catch (error) {
        console.error('Erro ao atualizar cidade:', error);
    }
}

function atualizarTituloModal(fonte) {
    const tituloElement = document.querySelector('#modalEnderecoPedido .bg-success h6');
    if (tituloElement) {
        if (fonte === 'receita') {
            tituloElement.innerHTML = '<i class="fas fa-truck"></i> Endereco de Entrega da Receita';
        } else {
            tituloElement.innerHTML = '<i class="fas fa-truck"></i> Endereco de Entrega';
        }
    }
}

function criarModalEnderecoPedido(fonte) {
    fonte = fonte || 'carteira';
    var tituloEndereco = fonte === 'receita'
        ? 'Endereco de Entrega da Receita'
        : 'Endereco de Entrega';

    var modal = document.createElement('div');
    modal.id = 'modalEnderecoPedido';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.innerHTML = '<div class="modal-dialog modal-lg"><div class="modal-content">' +
        '<div class="modal-header"><h5 class="modal-title"><i class="fas fa-map-marker-alt"></i> Endereco de Entrega</h5>' +
        '<button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>' +
        '<div class="modal-body"><div class="row">' +
        '<div class="col-md-6"><div class="card h-100"><div class="card-header"><h6 class="mb-0"><i class="fas fa-user"></i> Cliente</h6></div>' +
        '<div class="card-body"><ul class="list-unstyled mb-0">' +
        '<li class="mb-2"><strong>Razao Social:</strong><br><span id="modal_razao_social">-</span></li>' +
        '<li class="mb-2"><strong>CNPJ:</strong><br><span id="modal_cnpj_cliente">-</span></li>' +
        '<li class="mb-2"><strong>Municipio/UF:</strong><br><span id="modal_cliente_municipio">-</span></li>' +
        '<li class="mb-2"><strong>Incoterm:</strong><br><span id="modal_incoterm" class="badge bg-warning text-dark">-</span></li>' +
        '</ul></div></div></div>' +
        '<div class="col-md-6"><div class="card h-100"><div class="card-header bg-success text-white"><h6 class="mb-0"><i class="fas fa-truck"></i> ' + tituloEndereco + '</h6></div>' +
        '<div class="card-body"><ul class="list-unstyled mb-0">' +
        '<li class="mb-2"><strong>Empresa:</strong><br><span id="modal_empresa_entrega">-</span></li>' +
        '<li class="mb-2"><strong>CNPJ:</strong><br><span id="modal_cnpj_entrega">-</span></li>' +
        '<li class="mb-2"><strong>Endereco:</strong><br><span id="modal_endereco_completo">-</span></li>' +
        '<li class="mb-2"><strong>CEP:</strong> <span id="modal_cep_entrega">-</span></li>' +
        '<li class="mb-2"><strong>Telefone:</strong> <span id="modal_telefone_entrega">-</span></li>' +
        '</ul></div></div></div></div>' +
        '<div class="row mt-3"><div class="col-12"><div class="card"><div class="card-header"><h6 class="mb-0"><i class="fas fa-sticky-note"></i> Observacoes</h6></div>' +
        '<div class="card-body"><p id="modal_observacoes" class="mb-0">-</p></div></div></div></div></div>' +
        '<div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button></div>' +
        '</div></div>';
    document.body.appendChild(modal);
}

function preencherDadosEnderecoPedido(dados, fonte) {
    document.getElementById('modal_razao_social').textContent = dados.raz_social || '-';
    document.getElementById('modal_cnpj_cliente').textContent = dados.cnpj_cpf || '-';
    document.getElementById('modal_cliente_municipio').textContent =
        (dados.municipio || '-') + ' / ' + (dados.estado || '-');
    document.getElementById('modal_incoterm').textContent = dados.incoterm || '-';

    document.getElementById('modal_empresa_entrega').textContent = dados.empresa_endereco_ent || '-';
    document.getElementById('modal_cnpj_entrega').textContent = dados.cnpj_endereco_ent || '-';

    var enderecoCompleto = [
        dados.rua_endereco_ent,
        dados.endereco_ent ? 'n ' + dados.endereco_ent : null,
        dados.bairro_endereco_ent,
        dados.nome_cidade,
        dados.cod_uf
    ].filter(Boolean).join(', ');

    document.getElementById('modal_endereco_completo').textContent = enderecoCompleto || '-';
    document.getElementById('modal_cep_entrega').textContent = dados.cep_endereco_ent || '-';
    document.getElementById('modal_telefone_entrega').textContent = dados.telefone_endereco_ent || '-';

    document.getElementById('modal_observacoes').textContent = dados.observ_ped_1 || 'Sem observacoes';

    if (dados.incoterm && (dados.incoterm.includes('RED') || dados.incoterm.includes('REDESPACHO'))) {
        document.getElementById('modal_incoterm').className = 'badge bg-danger';
        var headerEntrega = document.querySelector('#modalEnderecoPedido .bg-success');
        if (headerEntrega) {
            headerEntrega.innerHTML = '<h6 class="mb-0"><i class="fas fa-truck"></i> Endereco de Entrega <span class="badge bg-danger-subtle text-danger ms-2">REDESPACHO</span></h6>';
        }
    }
}
