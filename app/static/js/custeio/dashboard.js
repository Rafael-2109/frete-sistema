/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Dashboard JavaScript
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    carregarEstatisticas();
});

// ==========================================================================
// ESTATISTICAS
// ==========================================================================
function carregarEstatisticas() {
    fetch('/custeio/api/dashboard/estatisticas')
        .then(r => r.json())
        .then(data => {
            if (data.sucesso) {
                document.getElementById('stat-produtos-custeados').textContent = data.produtos_custeados || 0;
                document.getElementById('stat-comprados').textContent = data.comprados || 0;
                document.getElementById('stat-produzidos').textContent = data.produzidos || 0;
                document.getElementById('stat-fretes').textContent = data.fretes || 0;

                // Banner de dormencia (>30 dias = warning, >90 dias = critico)
                const dormenciaEl = document.getElementById('alerta-dormencia');
                const dormenciaMsgEl = document.getElementById('alerta-dormencia-msg');
                if (data.dias_dormencia !== null && data.dias_dormencia !== undefined && data.dias_dormencia > 30) {
                    dormenciaEl.classList.remove('d-none', 'alert-warning', 'alert-danger');
                    if (data.dias_dormencia > 90) {
                        dormenciaEl.classList.add('alert-danger');
                        dormenciaMsgEl.innerHTML = `<strong>CRITICO:</strong> Custos desatualizados ha <strong>${data.dias_dormencia} dias</strong> ` +
                            `(ultima atualizacao: ${data.ultima_atualizacao}). Fechamento mensal deve ocorrer automaticamente todo dia 5 as 04:00.`;
                    } else {
                        dormenciaEl.classList.add('alert-warning');
                        dormenciaMsgEl.innerHTML = `Custos desatualizados ha <strong>${data.dias_dormencia} dias</strong> ` +
                            `(ultima atualizacao: ${data.ultima_atualizacao}).`;
                    }
                } else {
                    dormenciaEl.classList.add('d-none');
                }

                // Banner de produtos sem custo
                const semCustoEl = document.getElementById('alerta-sem-custo');
                const semCustoMsgEl = document.getElementById('alerta-sem-custo-msg');
                if (data.produtos_sem_custo && data.produtos_sem_custo > 0) {
                    semCustoEl.classList.remove('d-none');
                    semCustoMsgEl.innerHTML = `<strong>${data.produtos_sem_custo} produtos ativos sem custo cadastrado</strong> ` +
                        `(de ${data.produtos_ativos_total || 0} ativos). Pedidos desses produtos ficam com margem nao calculada.`;
                } else {
                    semCustoEl.classList.add('d-none');
                }
            }
        })
        .catch(err => console.error('Erro ao carregar estatisticas:', err));
}

// ==========================================================================
// MODAL CUSTO OPERACAO
// ==========================================================================
function abrirModalOperacao() {
    fetch('/custeio/api/parametros/obter/CUSTO_OPERACAO_PERCENTUAL')
        .then(r => r.json())
        .then(data => {
            if (data.sucesso || data.valor !== undefined) {
                document.getElementById('operacao-percentual').value = data.valor || '';
                document.getElementById('operacao-descricao').value = data.descricao || '';
                document.getElementById('operacao-atualizado').textContent = data.atualizado_em || '-';
            } else {
                document.getElementById('operacao-percentual').value = '';
                document.getElementById('operacao-descricao').value = '';
                document.getElementById('operacao-atualizado').textContent = '-';
            }
        })
        .catch(() => {
            document.getElementById('operacao-percentual').value = '';
            document.getElementById('operacao-descricao').value = '';
            document.getElementById('operacao-atualizado').textContent = '-';
        });

    new bootstrap.Modal(document.getElementById('modalOperacao')).show();
}

function salvarCustoOperacao() {
    const percentual = parseFloat(document.getElementById('operacao-percentual').value);
    const descricao = document.getElementById('operacao-descricao').value;

    if (isNaN(percentual)) {
        alert('Informe um percentual valido');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/parametros/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            chave: 'CUSTO_OPERACAO_PERCENTUAL',
            valor: percentual,
            descricao: descricao || 'Custo operacional sobre produtos'
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalOperacao')).hide();
            alert('Custo de operacao salvo com sucesso!');
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        console.error(err);
        alert('Erro ao salvar');
    });
}

// ==========================================================================
// LOADING
// ==========================================================================
function mostrarLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.toggle('show', show);
    }
}
