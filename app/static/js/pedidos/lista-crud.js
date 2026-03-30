/**
 * lista-crud.js — CRUD de pedidos (mapa, embarque FOB, excluir, desvincular, editar, reset)
 * Extraido de lista_pedidos.html (linhas 1887-2008, 2176-2305)
 */

function abrirMapaPedidos() {
    const selectedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');

    if (selectedCheckboxes.length === 0) {
        alert('Por favor, selecione pelo menos um pedido para visualizar no mapa.');
        return false;
    }

    const pedidoNumeros = [];
    selectedCheckboxes.forEach(checkbox => {
        const row = checkbox.closest('tr');
        const numPedido = row.querySelector('td:nth-child(3) strong').textContent.trim();
        pedidoNumeros.push(numPedido);
    });

    const params = new URLSearchParams();
    pedidoNumeros.forEach(num => params.append('pedidos[]', num));

    const url = '/carteira/mapa/visualizar?' + params.toString();
    window.open(url, '_blank');
}

function abrirEmbarqueFOB() {
    const selectedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');

    if (selectedCheckboxes.length === 0) {
        alert('Por favor, selecione pelo menos um pedido para embarque FOB.');
        return false;
    }

    const pedidoIds = Array.from(selectedCheckboxes).map(cb => cb.value);

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.PEDIDOS_URLS.embarqueFob;

    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrf_token';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);

    pedidoIds.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'separacao_lote_ids';
        input.value = id;
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
}

function confirmarExclusao(loteId, numeroPedido) {
    const mensagem = 'Tem certeza que deseja excluir o pedido ' + numeroPedido + '?\n\nATENCAO: Esta acao tambem removera todos os itens de separacao relacionados e NAO PODE SER DESFEITA!';

    if (confirm(mensagem)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/pedidos/excluir/' + loteId;

        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);

        document.body.appendChild(form);
        form.submit();
    }
}

function confirmarDesvinculacao(loteId, numeroPedido) {
    const mensagem = 'DESVINCULACAO DE EMBARQUE CANCELADO\n\n' +
                    'Pedido: ' + numeroPedido + '\n\n' +
                    'Esta acao ira:\n' +
                    '- Remover vinculos orfaos com embarques cancelados\n' +
                    '- Limpar dados de cotacao/transporte/NF obsoletos\n' +
                    '- Garantir que o pedido fique 100% ABERTO\n' +
                    '- Permitir edicao/exclusao/nova cotacao sem problemas\n\n' +
                    'IMPORTANTE: Funciona para pedidos ABERTO/EMBARCADO/COTADO\n' +
                    'que estao com vinculos orfaos de embarques cancelados.\n\n' +
                    'Deseja continuar?';

    if (confirm(mensagem)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/embarques/admin/desvincular-pedido/' + loteId;

        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);

        document.body.appendChild(form);
        form.submit();
    }
}

function abrirEdicaoPedido(loteId) {
    fetch('/pedidos/editar/' + loteId + '?ajax=1')
        .then(response => response.text())
        .then(html => {
            const modalExistente = document.getElementById('modalEdicaoPedido');
            if (modalExistente) modalExistente.remove();

            const modalHtml = '<div class="modal fade" id="modalEdicaoPedido" tabindex="-1">' +
                '<div class="modal-dialog modal-lg">' +
                '<div class="modal-content">' +
                '<div class="modal-header">' +
                '<h5 class="modal-title"><i class="fas fa-edit"></i> Editar Pedido</h5>' +
                '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>' +
                '</div>' +
                '<div class="modal-body">' + html + '</div>' +
                '</div></div></div>';

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modal = new bootstrap.Modal(document.getElementById('modalEdicaoPedido'));
            modal.show();

            const form = document.querySelector('#modalEdicaoPedido form');
            if (form) {
                form.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const formData = new FormData(form);

                    fetch(form.action, { method: 'POST', body: formData })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            modal.hide();
                            window.location.reload();
                        } else {
                            if (data.errors) {
                                let errorMessage = 'Erros encontrados:\n';
                                for (let field in data.errors) {
                                    errorMessage += '- ' + field + ': ' + data.errors[field].join(', ') + '\n';
                                }
                                alert(errorMessage);
                            } else {
                                alert(data.message || 'Erro ao salvar pedido');
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        alert('Erro ao processar requisicao');
                    });
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar formulario:', error);
            alert('Erro ao carregar formulario de edicao');
        });
}

function resetStatusPedido(loteId) {
    if (!confirm('Tem certeza que deseja resetar o status deste pedido?\n\nIsso ira:\n- Limpar a NF atual\n- Buscar NF em EmbarqueItem ativo\n- Recalcular o status baseado em EmbarqueItem e FaturamentoProduto')) {
        return;
    }

    const btnReset = event.target;
    const textoOriginal = btnReset.innerHTML;
    btnReset.disabled = true;
    btnReset.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';

    fetch('/pedidos/reset_status/' + loteId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Status resetado com sucesso!\n\nStatus anterior: ' + data.status_anterior + '\nStatus novo: ' + data.status_novo + '\nNF: ' + (data.nf || 'Nao encontrada'));
            window.location.reload();
        } else {
            alert('Erro ao resetar status: ' + data.message);
            btnReset.disabled = false;
            btnReset.innerHTML = textoOriginal;
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao processar requisicao');
        btnReset.disabled = false;
        btnReset.innerHTML = textoOriginal;
    });
}

function cancelarSeparacao(loteId) {
    abrirModalMotivoExclusao(loteId);
}
