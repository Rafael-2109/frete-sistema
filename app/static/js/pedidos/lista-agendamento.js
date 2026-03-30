/**
 * lista-agendamento.js — Modal de contato de agendamento + confirmar/reverter
 * Extraido de lista_pedidos.html (linhas 2010-2174, 2623-2686)
 */

function mostrarContatoAgendamento(btn) {
    const cnpj = btn.dataset.cnpj;
    const cadastrado = btn.dataset.cadastrado === 'true';
    const forma = btn.dataset.forma || '';
    const contato = btn.dataset.contato || '';
    const observacao = btn.dataset.observacao || '';
    const naoAceitaPallet = btn.dataset.naoAceitaPallet === 'true';
    const horarioDe = btn.dataset.horarioDe || '';
    const horarioAte = btn.dataset.horarioAte || '';
    const obsRecebimento = btn.dataset.obsRecebimento || '';

    const titulo = cadastrado ? 'Editar Agendamento' : 'Cadastrar Agendamento';

    const modalHtml = '<div class="modal fade" id="modalContatoAgendamento" tabindex="-1">' +
        '<div class="modal-dialog"><div class="modal-content">' +
        '<div class="modal-header"><h5 class="modal-title"><i class="fas fa-calendar-alt"></i> ' + titulo + '</h5>' +
        '<button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>' +
        '<div class="modal-body">' +
        '<div class="mb-2"><label class="form-label"><strong>CNPJ:</strong></label><div class="form-control-plaintext">' + cnpj + '</div></div>' +
        '<div class="row mb-2"><div class="col-md-6"><label for="cag-forma" class="form-label">Forma de Agendamento</label>' +
        '<select id="cag-forma" class="form-select">' +
        '<option value="">-- Selecione --</option>' +
        '<option value="PORTAL"' + (forma === 'PORTAL' ? ' selected' : '') + '>PORTAL</option>' +
        '<option value="TELEFONE"' + (forma === 'TELEFONE' ? ' selected' : '') + '>TELEFONE</option>' +
        '<option value="E-MAIL"' + (forma === 'E-MAIL' ? ' selected' : '') + '>E-MAIL</option>' +
        '<option value="COMERCIAL"' + (forma === 'COMERCIAL' ? ' selected' : '') + '>COMERCIAL</option>' +
        '<option value="SEM AGENDAMENTO"' + (forma === 'SEM AGENDAMENTO' ? ' selected' : '') + '>SEM AGENDAMENTO</option>' +
        '<option value="ODOO"' + (forma === 'ODOO' ? ' selected' : '') + '>ODOO</option>' +
        '</select></div>' +
        '<div class="col-md-6"><label for="cag-contato" class="form-label">Contato</label>' +
        '<input type="text" id="cag-contato" class="form-control" value="' + contato + '"></div></div>' +
        '<div class="mb-2"><label for="cag-observacao" class="form-label">Observacao</label>' +
        '<textarea id="cag-observacao" class="form-control" rows="2">' + observacao + '</textarea></div>' +
        '<hr><h6 class="text-muted"><i class="fas fa-truck-loading"></i> Dados de Recebimento</h6>' +
        '<div class="row mb-2"><div class="col-md-4"><label for="cag-horario-de" class="form-label">Horario De</label>' +
        '<input type="time" id="cag-horario-de" class="form-control" value="' + horarioDe + '"></div>' +
        '<div class="col-md-4"><label for="cag-horario-ate" class="form-label">Horario Ate</label>' +
        '<input type="time" id="cag-horario-ate" class="form-control" value="' + horarioAte + '"></div>' +
        '<div class="col-md-4 d-flex align-items-end"><div class="form-check">' +
        '<input class="form-check-input" type="checkbox" id="cag-pallet"' + (naoAceitaPallet ? ' checked' : '') + '>' +
        '<label class="form-check-label" for="cag-pallet">Nao aceita NF Pallet</label></div></div></div>' +
        '<div class="mb-2"><label for="cag-obs-recebimento" class="form-label">Obs. Recebimento</label>' +
        '<textarea id="cag-obs-recebimento" class="form-control" rows="2" placeholder="Ex: 1 SKU por pallet...">' + obsRecebimento + '</textarea></div>' +
        '</div>' +
        '<div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>' +
        '<button type="button" class="btn btn-success" onclick="salvarContatoAgendamento(\'' + cnpj + '\', ' + cadastrado + ', this)">' +
        '<i class="fas fa-save"></i> Salvar</button></div>' +
        '</div></div></div>';

    const modalExistente = document.getElementById('modalContatoAgendamento');
    if (modalExistente) modalExistente.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('modalContatoAgendamento'));
    modal.show();
}

function salvarContatoAgendamento(cnpj, cadastrado, btnEl) {
    const dados = {
        cnpj: cnpj,
        forma: document.getElementById('cag-forma').value,
        contato: document.getElementById('cag-contato').value,
        observacao: document.getElementById('cag-observacao').value,
        nao_aceita_nf_pallet: document.getElementById('cag-pallet').checked,
        horario_recebimento_de: document.getElementById('cag-horario-de').value,
        horario_recebimento_ate: document.getElementById('cag-horario-ate').value,
        observacoes_recebimento: document.getElementById('cag-obs-recebimento').value,
    };

    const url = cadastrado
        ? '/cadastros-agendamento/api/atualizar/' + encodeURIComponent(cnpj)
        : '/cadastros-agendamento/api/criar';
    const method = cadastrado ? 'PUT' : 'POST';

    btnEl.disabled = true;
    btnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

    const csrfTokenValue = document.querySelector('input[name="csrf_token"]').value;

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfTokenValue
        },
        body: JSON.stringify(dados)
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalContatoAgendamento')).hide();
            const btns = document.querySelectorAll('button[data-cnpj="' + cnpj + '"]');
            btns.forEach(b => {
                b.dataset.forma = dados.forma;
                b.dataset.contato = dados.contato;
                b.dataset.observacao = dados.observacao;
                b.dataset.naoAceitaPallet = dados.nao_aceita_nf_pallet ? 'true' : 'false';
                b.dataset.horarioDe = dados.horario_recebimento_de || '';
                b.dataset.horarioAte = dados.horario_recebimento_ate || '';
                b.dataset.obsRecebimento = dados.observacoes_recebimento || '';
                b.dataset.cadastrado = 'true';
                if (dados.forma) {
                    b.className = 'btn btn-sm btn-primary';
                    b.textContent = dados.forma;
                }
            });
            const toast = document.createElement('div');
            toast.className = 'alert alert-success position-fixed bottom-0 end-0 m-3';
            toast.style.zIndex = '9999';
            toast.innerHTML = '<i class="fas fa-check"></i> Salvo com sucesso';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        } else {
            alert(data.error || 'Erro ao salvar');
            btnEl.disabled = false;
            btnEl.innerHTML = '<i class="fas fa-save"></i> Salvar';
        }
    })
    .catch(err => {
        alert('Erro de conexao: ' + err.message);
        btnEl.disabled = false;
        btnEl.innerHTML = '<i class="fas fa-save"></i> Salvar';
    });
}

function confirmarAgendamento(separacaoLoteId, numPedido) {
    if (!separacaoLoteId) {
        alert('Este pedido nao possui separacao para confirmar agendamento.');
        return;
    }

    if (!confirm('Confirmar agendamento do pedido ' + numPedido + '?')) return;

    fetch('/carteira/api/separacao/' + separacaoLoteId + '/confirmar-agendamento', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Agendamento confirmado com sucesso!');
            location.reload();
        } else {
            alert('Erro ao confirmar agendamento: ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro ao confirmar agendamento:', error);
        alert('Erro ao confirmar agendamento');
    });
}

function reverterConfirmacaoAgendamento(separacaoLoteId, numPedido) {
    if (!separacaoLoteId) {
        alert('Este pedido nao possui separacao para reverter confirmacao.');
        return;
    }

    if (!confirm('Reverter confirmacao de agendamento do pedido ' + numPedido + '?')) return;

    fetch('/carteira/api/separacao/' + separacaoLoteId + '/reverter-agendamento', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Confirmacao de agendamento revertida!');
            location.reload();
        } else {
            alert('Erro ao reverter confirmacao: ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro ao reverter confirmacao:', error);
        alert('Erro ao reverter confirmacao');
    });
}
