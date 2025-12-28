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
