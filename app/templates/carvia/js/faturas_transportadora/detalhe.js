function formatarValor(v) {
    if (v === null || v === undefined) return '-';
    return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ====== Download PDF ======
function downloadFaturaTranspPdf(faturaId) {
    fetch(`/carvia/api/fatura-transportadora/${faturaId}/pdf`)
        .then(r => r.json())
        .then(data => {
            if (data.sucesso && data.url) {
                window.open(data.url, '_blank');
            } else {
                alert(data.mensagem || data.erro || 'Erro ao obter arquivo');
            }
        })
        .catch(() => alert('Erro de conexao ao baixar arquivo'));
}

// ====== Conferencia de Subcontrato ======
let confSubId = null;

function conferirSubcontrato(subId) {
    confSubId = subId;
    const loading = document.getElementById('conf-loading');
    const erro = document.getElementById('conf-erro');
    const conteudo = document.getElementById('conf-conteudo');

    loading.classList.remove('d-none');
    erro.classList.add('d-none');
    conteudo.classList.add('d-none');
    document.getElementById('conf-breakdown').classList.add('d-none');

    new bootstrap.Modal(document.getElementById('modalConferenciaSubcontrato')).show();

    fetch(`/carvia/api/conferencia-subcontrato/${subId}/calcular`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CARVIA_DATA.csrfToken,
        },
    })
    .then(r => r.json())
    .then(data => {
        loading.classList.add('d-none');

        if (!data.sucesso) {
            erro.textContent = data.erro || 'Erro ao calcular conferencia.';
            erro.classList.remove('d-none');
            return;
        }

        // Preencher dados do subcontrato
        const sub = data.subcontrato_info;
        const op = data.operacao_info;

        document.getElementById('modalConferenciaLabel').innerHTML =
            `<i class="fas fa-search-dollar"></i> Conferencia — ${sub.cte_numero || 'Aguardando emissao'}`;

        document.getElementById('conf-cte-valor').textContent = formatarValor(sub.cte_valor);
        document.getElementById('conf-valor-cotado').textContent = formatarValor(sub.valor_cotado);
        document.getElementById('conf-valor-final').textContent = formatarValor(sub.valor_final);
        document.getElementById('conf-rota').textContent =
            `${op.uf_origem || 'SP'} → ${op.uf_destino} — ${op.cidade_destino || '?'}`;
        document.getElementById('conf-cliente').textContent = op.nome_cliente || '-';
        document.getElementById('conf-peso').textContent =
            `${Number(op.peso).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} kg`;
        document.getElementById('conf-total-opcoes').textContent = data.total_opcoes;

        // Preencher tabela de opcoes
        const tbody = document.getElementById('conf-tbody-opcoes');
        tbody.innerHTML = '';
        const semOpcoes = document.getElementById('conf-sem-opcoes');
        const tabelaOpcoes = document.getElementById('conf-tabela-opcoes');

        if (data.opcoes.length === 0) {
            semOpcoes.classList.remove('d-none');
            tabelaOpcoes.classList.add('d-none');
        } else {
            semOpcoes.classList.add('d-none');
            tabelaOpcoes.classList.remove('d-none');

            let menorValor = Infinity;
            data.opcoes.forEach((op, idx) => {
                if (op.valor_frete < menorValor) menorValor = op.valor_frete;
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${op.tabela_nome || '-'}</strong>
                        <div class="small text-muted">${op.transportadora_nome || ''}</div></td>
                    <td>${op.tipo_carga || '-'}</td>
                    <td>${op.modalidade || '-'}</td>
                    <td class="valor-col"><strong>${formatarValor(op.valor_frete)}</strong></td>
                    <td>
                        <button type="button" class="btn btn-sm btn-outline-info py-0 px-1"
                                onclick="mostrarBreakdown(${idx})" title="Ver breakdown">
                            <i class="fas fa-info-circle"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Pre-popular valor_considerado com menor valor
            document.getElementById('conf-valor-considerado').value = menorValor.toFixed(2);
        }

        // Se ja tinha conferencia, pre-popular
        if (sub.valor_considerado) {
            document.getElementById('conf-valor-considerado').value = sub.valor_considerado.toFixed(2);
        }
        if (sub.status_conferencia === 'DIVERGENTE') {
            document.getElementById('conf-status-divergente').checked = true;
        } else {
            document.getElementById('conf-status-aprovado').checked = true;
        }

        // Guardar opcoes para breakdown
        window._confOpcoes = data.opcoes;

        conteudo.classList.remove('d-none');
    })
    .catch(err => {
        loading.classList.add('d-none');
        erro.textContent = 'Erro de conexao: ' + err.message;
        erro.classList.remove('d-none');
    });
}

function mostrarBreakdown(idx) {
    const opcao = window._confOpcoes[idx];
    if (!opcao || !opcao.descritivo) return;

    const titulo = document.getElementById('conf-breakdown-titulo');
    titulo.textContent = `Breakdown — ${opcao.tabela_nome || 'Tabela ' + (idx + 1)}`;

    const tbody = document.getElementById('conf-tbody-breakdown');
    tbody.innerHTML = '';

    opcao.descritivo.forEach(linha => {
        const tr = document.createElement('tr');
        const isTotal = linha.is_total || linha.is_subtotal;
        tr.innerHTML = `
            <td${isTotal ? ' class="fw-bold"' : ''}>${linha.componente}</td>
            <td>${linha.fator || ''}</td>
            <td>${linha.base || ''}</td>
            <td class="valor-col${isTotal ? ' fw-bold' : ''}">${formatarValor(linha.resultado)}</td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('conf-breakdown').classList.remove('d-none');
}

// Salvar conferencia
document.getElementById('btn-salvar-conferencia')?.addEventListener('click', function() {
    if (!confSubId) return;

    const valorInput = document.getElementById('conf-valor-considerado');
    const valor = parseFloat(valorInput.value);
    if (isNaN(valor) || valor < 0) {
        valorInput.classList.add('is-invalid');
        return;
    }
    valorInput.classList.remove('is-invalid');

    const status = document.querySelector('input[name="conf-status"]:checked').value;
    const observacoes = document.getElementById('conf-observacoes').value.trim();

    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

    fetch(`/carvia/api/conferencia-subcontrato/${confSubId}/registrar`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CARVIA_DATA.csrfToken,
        },
        body: JSON.stringify({
            valor_considerado: valor,
            status: status,
            observacoes: observacoes,
        }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            // Atualizar badge na tabela
            const badgeCell = document.getElementById(`sub-conf-badge-${confSubId}`);
            if (badgeCell) {
                const badgeClass = data.status_conferencia === 'APROVADO' ? 'bg-success' : 'bg-danger';
                badgeCell.innerHTML = `<span class="badge ${badgeClass}">${data.status_conferencia}</span>`;
            }

            // Atualizar valor considerado na tabela
            const valCell = document.getElementById(`sub-val-cons-${confSubId}`);
            if (valCell) {
                valCell.textContent = formatarValor(data.valor_considerado);
            }

            // Se fatura mudou de status, recarregar pagina
            if (data.fatura_atualizada) {
                bootstrap.Modal.getInstance(document.getElementById('modalConferenciaSubcontrato')).hide();
                window.location.reload();
            } else {
                bootstrap.Modal.getInstance(document.getElementById('modalConferenciaSubcontrato')).hide();
            }
        } else {
            alert(data.erro || 'Erro ao salvar conferencia.');
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-save"></i> Salvar';
        }
    })
    .catch(err => {
        alert('Erro de conexao: ' + err.message);
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-save"></i> Salvar';
    });
});

// Reset botao ao fechar modal
document.getElementById('modalConferenciaSubcontrato')?.addEventListener('hidden.bs.modal', function() {
    const btn = document.getElementById('btn-salvar-conferencia');
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-save"></i> Salvar';
    confSubId = null;
});

// ====== Modal Anexar Subcontratos ======
const btnAbrirAnexar = document.getElementById('btn-abrir-modal-anexar');
if (btnAbrirAnexar) {
    btnAbrirAnexar.addEventListener('click', function() {
        carregarSubcontratosDisponiveis();
        new bootstrap.Modal(document.getElementById('modalAnexarSubcontratos')).show();
    });
}

function carregarSubcontratosDisponiveis() {
    const loading = document.getElementById('anexar-loading');
    const vazio = document.getElementById('anexar-vazio');
    const tabela = document.getElementById('anexar-tabela');
    const erro = document.getElementById('anexar-erro');

    loading.classList.remove('d-none');
    vazio.classList.add('d-none');
    tabela.classList.add('d-none');
    erro.classList.add('d-none');
    document.getElementById('btn-confirmar-anexar').disabled = true;

    fetch(`/carvia/api/subcontratos-disponiveis/${CARVIA_DATA.transportadoraId}`)
        .then(r => r.json())
        .then(data => {
            loading.classList.add('d-none');

            if (!data.sucesso) {
                erro.textContent = data.erro || 'Erro ao carregar subcontratos.';
                erro.classList.remove('d-none');
                return;
            }

            const subs = data.subcontratos || [];
            if (subs.length === 0) {
                vazio.classList.remove('d-none');
                return;
            }

            document.getElementById('anexar-qtd').textContent = `${subs.length} subcontrato(s) disponivel(is)`;

            const tbody = document.getElementById('anexar-tbody');
            tbody.innerHTML = '';

            subs.forEach(sub => {
                const valorFinal = sub.valor_final ? `R$ ${sub.valor_final.toFixed(2)}` : '-';
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><input type="checkbox" class="sub-check-anexar" value="${sub.id}"></td>
                    <td><strong>${sub.cte_numero}</strong></td>
                    <td>${sub.cliente}</td>
                    <td>${sub.destino}</td>
                    <td class="valor-col"><strong>${valorFinal}</strong></td>
                `;
                tbody.appendChild(tr);
            });

            tabela.classList.remove('d-none');
            atualizarBtnAnexar();
        })
        .catch(err => {
            loading.classList.add('d-none');
            erro.textContent = 'Erro de conexao: ' + err.message;
            erro.classList.remove('d-none');
        });
}

// Checkboxes — ativar/desativar botao
document.getElementById('anexar-tbody')?.addEventListener('change', atualizarBtnAnexar);

document.getElementById('check-all-anexar')?.addEventListener('change', function() {
    document.querySelectorAll('.sub-check-anexar').forEach(cb => cb.checked = this.checked);
    atualizarBtnAnexar();
});

document.getElementById('btn-select-all-anexar')?.addEventListener('click', function() {
    const checkAll = document.getElementById('check-all-anexar');
    checkAll.checked = true;
    document.querySelectorAll('.sub-check-anexar').forEach(cb => cb.checked = true);
    atualizarBtnAnexar();
});

function atualizarBtnAnexar() {
    const selecionados = document.querySelectorAll('.sub-check-anexar:checked');
    const btn = document.getElementById('btn-confirmar-anexar');
    btn.disabled = selecionados.length === 0;
    btn.textContent = selecionados.length > 0
        ? `Anexar ${selecionados.length} Selecionado(s)`
        : 'Anexar Selecionados';
}

// Confirmar anexar
document.getElementById('btn-confirmar-anexar')?.addEventListener('click', function() {
    const ids = Array.from(document.querySelectorAll('.sub-check-anexar:checked'))
        .map(cb => parseInt(cb.value));

    if (ids.length === 0) return;

    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Anexando...';

    fetch(`/carvia/faturas-transportadora/${CARVIA_DATA.faturaId}/anexar-subcontratos`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CARVIA_DATA.csrfToken,
        },
        body: JSON.stringify({ subcontrato_ids: ids }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalAnexarSubcontratos')).hide();
            mostrarConfirmacaoValor(data.valor_total_fatura, data.soma_total_subcontratos);
        } else {
            const erro = document.getElementById('anexar-erro');
            erro.textContent = data.erro || 'Erro ao anexar subcontratos.';
            erro.classList.remove('d-none');
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-link"></i> Anexar Selecionados';
        }
    })
    .catch(err => {
        const erro = document.getElementById('anexar-erro');
        erro.textContent = 'Erro de conexao: ' + err.message;
        erro.classList.remove('d-none');
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-link"></i> Anexar Selecionados';
    });
});

// ====== Desanexar Subcontrato ======
function desanexarSubcontrato(subId, cteNumero) {
    if (!confirm(`Desanexar subcontrato ${cteNumero} desta fatura?`)) return;

    fetch(`/carvia/faturas-transportadora/${CARVIA_DATA.faturaId}/desanexar-subcontrato/${subId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CARVIA_DATA.csrfToken,
        },
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            mostrarConfirmacaoValor(data.valor_total_fatura, data.soma_valores_restantes);
        } else {
            alert(data.erro || 'Erro ao desanexar subcontrato.');
        }
    })
    .catch(err => alert('Erro de conexao: ' + err.message));
}

// ====== Modal Confirmacao de Valor ======
let pendingSomaSubcontratos = 0;

function mostrarConfirmacaoValor(valorAtualFatura, somaSubcontratos) {
    const diff = Math.abs(valorAtualFatura - somaSubcontratos);

    // Se diferenca < 1 centavo ou nao ha subcontratos, recarregar direto
    if (diff < 0.01 || somaSubcontratos === 0) {
        window.location.reload();
        return;
    }

    // Mostrar modal perguntando se quer atualizar
    pendingSomaSubcontratos = somaSubcontratos;
    document.getElementById('cv-valor-atual').textContent = `R$ ${valorAtualFatura.toFixed(2)}`;
    document.getElementById('cv-soma-subs').textContent = `R$ ${somaSubcontratos.toFixed(2)}`;

    new bootstrap.Modal(document.getElementById('modalConfirmarValor')).show();
}

document.getElementById('btn-manter-valor')?.addEventListener('click', function() {
    bootstrap.Modal.getInstance(document.getElementById('modalConfirmarValor')).hide();
    window.location.reload();
});

document.getElementById('btn-atualizar-valor')?.addEventListener('click', function() {
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    fetch(`/carvia/faturas-transportadora/${CARVIA_DATA.faturaId}/atualizar-valor`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CARVIA_DATA.csrfToken,
        },
        body: JSON.stringify({ valor_total: pendingSomaSubcontratos }),
    })
    .then(r => r.json())
    .then(data => {
        bootstrap.Modal.getInstance(document.getElementById('modalConfirmarValor')).hide();
        window.location.reload();
    })
    .catch(() => {
        bootstrap.Modal.getInstance(document.getElementById('modalConfirmarValor')).hide();
        window.location.reload();
    });
});
