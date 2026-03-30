/**
 * lista-nf.js — Validacao NF, gravacao NF e monitoramento + sincronizar items
 * Extraido de lista_pedidos.html (linhas 2307-2432, 2935-2986)
 */

function validarNF(loteId) {
    const inputNF = document.getElementById('input_numero_nf');
    const numeroNF = inputNF.value.trim();

    if (!numeroNF) {
        alert('Por favor, preencha o numero da NF antes de validar');
        return;
    }

    const badgeSincronizacao = document.getElementById('badge-sincronizacao');
    const mensagemValidacao = document.getElementById('mensagem-validacao');
    badgeSincronizacao.innerHTML = '<span class="badge bg-warning text-dark fs-6"><i class="fas fa-spinner fa-spin"></i> Validando e gravando...</span>';

    fetch('/pedidos/gravar_nf/' + loteId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({ numero_nf: numeroNF })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.existe) {
                if (data.sincronizado_nf) {
                    badgeSincronizacao.innerHTML = '<span class="badge bg-success fs-6">Sincronizado</span>';
                    mensagemValidacao.textContent = data.message;
                    mensagemValidacao.className = 'text-success';
                } else {
                    badgeSincronizacao.innerHTML = '<span class="badge bg-danger fs-6">NF Cancelada</span>';
                    mensagemValidacao.textContent = data.message;
                    mensagemValidacao.className = 'text-danger';
                }
            } else {
                badgeSincronizacao.innerHTML = '<span class="badge bg-warning text-dark fs-6">Nao encontrada</span>';
                mensagemValidacao.textContent = data.message;
                mensagemValidacao.className = 'text-warning';
            }
            alert(data.message);
        } else {
            badgeSincronizacao.innerHTML = '<span class="badge bg-danger fs-6">Erro</span>';
            mensagemValidacao.textContent = data.message || 'Erro ao validar/gravar NF';
            mensagemValidacao.className = 'text-danger';
            alert(data.message || 'Erro ao validar/gravar NF');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        badgeSincronizacao.innerHTML = '<span class="badge bg-danger fs-6">Erro</span>';
        mensagemValidacao.textContent = 'Erro ao validar/gravar NF';
        mensagemValidacao.className = 'text-danger';
        alert('Erro ao validar/gravar NF: ' + error.message);
    });
}

function verificarMonitoramento(loteId, numeroNF) {
    const statusMonitoramento = document.getElementById('status-monitoramento');
    const infoMonitoramento = document.getElementById('info-monitoramento');
    statusMonitoramento.innerHTML = '<span class="badge bg-warning text-dark"><i class="fas fa-spinner fa-spin"></i> Verificando...</span>';

    fetch('/pedidos/verificar_monitoramento', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({ lote_id: loteId, numero_nf: numeroNF })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.encontrado) {
                const nfCdMonitoramento = data.nf_cd;
                const toggleNfCd = document.getElementById('toggle_nf_cd');

                if (nfCdMonitoramento) {
                    statusMonitoramento.innerHTML = '<span class="badge bg-danger fs-6">NF no CD</span>';
                    infoMonitoramento.textContent = 'NF esta marcada como "no CD" no monitoramento';
                } else {
                    statusMonitoramento.innerHTML = '<span class="badge bg-success fs-6">Ativa</span>';
                    infoMonitoramento.textContent = 'NF esta ativa no monitoramento';
                }

                if (toggleNfCd.checked !== nfCdMonitoramento) {
                    const msg = nfCdMonitoramento
                        ? 'O monitoramento indica "NF no CD". Deseja sincronizar aqui tambem?'
                        : 'O monitoramento indica "NF Ativa". Deseja sincronizar aqui tambem?';
                    if (confirm(msg)) {
                        toggleNfCd.checked = nfCdMonitoramento;
                    }
                }
            } else {
                statusMonitoramento.innerHTML = '<span class="badge bg-secondary">Nao encontrado</span>';
                infoMonitoramento.textContent = data.message || 'NF nao encontrada no monitoramento';
            }
        } else {
            statusMonitoramento.innerHTML = '<span class="badge bg-danger">Erro</span>';
            infoMonitoramento.textContent = data.message || 'Erro ao verificar monitoramento';
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        statusMonitoramento.innerHTML = '<span class="badge bg-danger">Erro</span>';
        infoMonitoramento.textContent = 'Erro ao conectar com o servidor';
    });
}

function sincronizarItemsFaturamento(loteId) {
    if (!confirm('Tem certeza que deseja sincronizar os items com o faturamento?\n\nIsso ira:\n- Buscar dados em FaturamentoProduto (qtd, valor, peso, pallet)\n- Atualizar TODOS os items da Separacao deste lote\n\nApenas items com sincronizado_nf=True serao atualizados')) {
        return;
    }

    const btnSync = event.target;
    const textoOriginal = btnSync.innerHTML;
    btnSync.disabled = true;
    btnSync.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sincronizando...';

    fetch('/pedidos/sincronizar-items-faturamento/' + loteId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const msg = 'Items sincronizados com sucesso!\n\n' +
                        'NF: ' + data.numero_nf + '\n' +
                        'Items atualizados: ' + data.atualizados + '\n' +
                        'Items adicionados: ' + (data.adicionados || 0) + '\n' +
                        'Items zerados: ' + (data.zerados || 0) + '\n' +
                        'Erros: ' + data.erros;
            alert(msg);

            const modal = bootstrap.Modal.getInstance(document.getElementById('modalEdicaoPedido'));
            if (modal) modal.hide();
            window.location.reload();
        } else {
            alert('Erro ao sincronizar items: ' + data.erro);
            btnSync.disabled = false;
            btnSync.innerHTML = textoOriginal;
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao sincronizar items: ' + error.message);
        btnSync.disabled = false;
        btnSync.innerHTML = textoOriginal;
    });
}
