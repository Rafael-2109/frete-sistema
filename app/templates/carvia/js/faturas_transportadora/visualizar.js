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
            // 2026-05-07: edicao de valor agora via tela dedicada
            // (`editar_fatura_transportadora`). Reload simples — se valor
            // da fatura divergir da soma, usuario edita manualmente.
            window.location.reload();
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
            window.location.reload();
        } else {
            alert(data.erro || 'Erro ao desanexar subcontrato.');
        }
    })
    .catch(err => alert('Erro de conexao: ' + err.message));
}

// Bloco "Modal Vincular Custos de Entrega" + "Desvincular Custo de Entrega" removido.
// Fluxo xerox Nacom: Despesas Extras sao criadas e vinculadas pelo CarviaFrete
// (rotas /carvia/despesas-extras/<id>/vincular-fatura). A tela da FaturaTransportadora
// mostra apenas leitura com acao "Ver Frete".

// JS dos modais inline `modalEditarValorTotal`, `modalConfirmarValor` e
// `modalAtualizarPdfFt` removido (2026-05-07) — edicao agora via pagina
// dedicada `editar_fatura_transportadora` (paridade Nacom).
