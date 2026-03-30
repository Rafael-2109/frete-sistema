/**
 * lista-cotacao.js — Verificacao NF CD e fluxo de cotacao
 * Extraido de lista_pedidos.html (linhas 1704-1885)
 */

function filterByStatus(status) {
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(function(row) {
        if (status === 'all') {
            row.style.display = '';
        } else {
            const statusBadge = row.querySelector('.badge');
            if (statusBadge && statusBadge.textContent.toLowerCase().includes(status.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}

function confirmCotacao() {
    const selectedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');

    if (selectedCheckboxes.length === 0) {
        alert('Por favor, selecione pelo menos um pedido para cotar.');
        return false;
    }

    const lotesSelecionados = Array.from(selectedCheckboxes).map(cb => cb.value);

    const btnCotar = document.getElementById('btnCotarFrete');
    const btnTextoOriginal = btnCotar.innerHTML;
    btnCotar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verificando...';
    btnCotar.disabled = true;

    fetch('/cotacao/verificar_nf_cd', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({ separacao_lote_ids: lotesSelecionados })
    })
    .then(response => response.json())
    .then(data => {
        btnCotar.innerHTML = btnTextoOriginal;
        btnCotar.disabled = false;

        if (!data.success) {
            alert(data.message || 'Erro ao verificar pedidos.');
            return;
        }

        if (!data.tem_pendentes) {
            const count = lotesSelecionados.length;
            if (confirm('Confirma a cotacao de ' + count + ' pedido(s) selecionado(s)?')) {
                submeterFormCotacao();
            }
            return;
        }

        preencherModalNfCd(data.selecionados, data.pendentes_nf_cd, data.pendentes_normais);
        const modal = new bootstrap.Modal(document.getElementById('modalNfCdPendentes'));
        modal.show();
    })
    .catch(error => {
        console.error('Erro na verificacao NF CD:', error);
        btnCotar.innerHTML = btnTextoOriginal;
        btnCotar.disabled = false;
        alert('Erro ao verificar pedidos com NF no CD. Tente novamente.');
    });

    return false;
}

function preencherModalNfCd(selecionados, pendentes_nf_cd, pendentes_normais) {
    const tbodySelecionados = document.getElementById('tabela_selecionados_cotacao');
    tbodySelecionados.innerHTML = '';

    selecionados.forEach(function(p) {
        tbodySelecionados.innerHTML += renderizarLinhaPedido(p, '');
    });

    const secaoNfCd = document.getElementById('secao_pendentes_nf_cd');
    const tbodyNfCd = document.getElementById('tabela_pendentes_nf_cd');
    tbodyNfCd.innerHTML = '';

    if (pendentes_nf_cd && pendentes_nf_cd.length > 0) {
        secaoNfCd.style.display = 'block';
        pendentes_nf_cd.forEach(function(p) {
            tbodyNfCd.innerHTML += renderizarLinhaPedido(p, 'table-warning');
        });
        document.getElementById('count_pendentes_nf_cd').textContent = pendentes_nf_cd.length;
    } else {
        secaoNfCd.style.display = 'none';
    }

    const secaoNormais = document.getElementById('secao_pendentes_normais');
    const tbodyNormais = document.getElementById('tabela_pendentes_normais');
    tbodyNormais.innerHTML = '';

    if (pendentes_normais && pendentes_normais.length > 0) {
        secaoNormais.style.display = 'block';
        pendentes_normais.forEach(function(p) {
            tbodyNormais.innerHTML += renderizarLinhaPedido(p, 'table-info');
        });
        document.getElementById('count_pendentes_normais').textContent = pendentes_normais.length;
    } else {
        secaoNormais.style.display = 'none';
    }

    document.getElementById('count_selecionados').textContent = selecionados.length;
}

function renderizarLinhaPedido(p, classeRow) {
    var confIcon = p.agendamento_confirmado
        ? '<i class="fas fa-check text-success"></i>'
        : '<span class="text-muted">-</span>';
    var statusBadge;
    if (p.status === 'NF no CD') {
        statusBadge = '<span class="badge bg-warning text-dark"><i class="fas fa-undo me-1"></i>NF no CD</span>';
    } else if (p.status === 'COTADO') {
        statusBadge = '<span class="badge bg-primary">' + p.status + '</span>';
    } else {
        statusBadge = '<span class="badge bg-secondary">' + (p.status || 'ABERTO') + '</span>';
    }

    return '<tr class="' + classeRow + '">' +
        '<td class="text-nowrap fw-semibold">' + (p.num_pedido || '-') + '</td>' +
        '<td class="text-nowrap"><small class="text-muted">' + (p.cnpj_cpf || '') + '</small><br><span class="fw-medium">' + (p.raz_social_red || '') + '</span></td>' +
        '<td class="text-nowrap">' + (p.nome_cidade || '') + '/' + (p.cod_uf || '') + '</td>' +
        '<td class="text-nowrap">' + (p.expedicao || '<span class="text-muted">-</span>') + '</td>' +
        '<td class="text-end text-nowrap">' + formatarValorBR(p.valor_saldo) + '</td>' +
        '<td class="text-end text-nowrap">' + formatarNumeroBR(p.peso, 1) + '</td>' +
        '<td class="text-end text-nowrap">' + formatarNumeroBR(p.pallet, 2) + '</td>' +
        '<td class="text-nowrap">' + (p.agendamento || '<span class="text-muted">-</span>') + '</td>' +
        '<td class="text-center">' + confIcon + '</td>' +
        '<td class="text-nowrap">' + (p.protocolo || '<span class="text-muted">-</span>') + '</td>' +
        '<td class="text-nowrap">' + (p.numero_nf || '<span class="text-muted">-</span>') + '</td>' +
        '<td class="text-nowrap"><small class="text-muted">' + (p.separacao_lote_id || '') + '</small></td>' +
        '<td>' + statusBadge + '</td>' +
    '</tr>';
}

function formatarValorBR(valor) {
    if (valor === null || valor === undefined) return '-';
    return valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatarNumeroBR(valor, decimais) {
    if (valor === null || valor === undefined) return '-';
    return valor.toLocaleString('pt-BR', { minimumFractionDigits: decimais, maximumFractionDigits: decimais });
}

function prosseguirCotacao() {
    var modalEl = document.getElementById('modalNfCdPendentes');
    var modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    submeterFormCotacao();
}

function submeterFormCotacao() {
    var form = document.querySelector('form[action*="/cotacao/iniciar"]');
    if (!form) {
        alert('Erro: formulario de cotacao nao encontrado.');
        return;
    }
    form.removeAttribute('onsubmit');
    form.submit();
}
