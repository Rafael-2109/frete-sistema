/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Parametros JavaScript
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosParametros = [];

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    carregarParametros();
    carregarCustoOperacao();
    carregarCustoFinanceiro();
});

// ==========================================================================
// CARREGAR DADOS
// ==========================================================================
function carregarParametros() {
    mostrarLoading(true);

    fetch('/custeio/api/parametros/listar')
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosParametros = data.dados;
                renderizarTabela(dadosParametros);
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
            alert('Erro ao carregar parametros');
        });
}

function carregarCustoOperacao() {
    fetch('/custeio/api/parametros/obter/CUSTO_OPERACAO_PERCENTUAL')
        .then(r => r.json())
        .then(data => {
            if (data.sucesso && data.parametro) {
                document.getElementById('operacao-percentual').value = data.parametro.valor;
                document.getElementById('operacao-atualizado').textContent =
                    data.parametro.atualizado_em || 'Nunca';
            }
        })
        .catch(err => console.error(err));
}

function carregarCustoFinanceiro() {
    fetch('/custeio/api/parametros/obter/CUSTO_FINANCEIRO_PERCENTUAL')
        .then(r => r.json())
        .then(data => {
            if (data.sucesso && data.parametro) {
                document.getElementById('financeiro-percentual').value = data.parametro.valor;
                document.getElementById('financeiro-atualizado').textContent =
                    data.parametro.atualizado_em || 'Nunca';
            }
        })
        .catch(err => console.error(err));
}

// ==========================================================================
// RENDERIZACAO
// ==========================================================================
function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-parametros');
    document.getElementById('total-registros').textContent = `${dados.length} parametro(s)`;

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum parametro cadastrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => {
        const isOperacao = item.chave === 'CUSTO_OPERACAO_PERCENTUAL';
        const isFinanceiro = item.chave === 'CUSTO_FINANCEIRO_PERCENTUAL';
        const valorFormatado = item.valor !== null ? item.valor.toFixed(2) : '-';
        const rowClass = isOperacao ? 'table-primary' : (isFinanceiro ? 'table-warning' : '');

        return `
            <tr class="${rowClass}">
                <td><code>${item.chave}</code></td>
                <td class="text-end">${valorFormatado}</td>
                <td>${item.descricao || '-'}</td>
                <td>${item.atualizado_em || '-'}</td>
                <td>${item.atualizado_por || '-'}</td>
                <td class="text-center">
                    <button class="btn btn-outline-primary btn-sm" onclick="editarParametro(${item.id})" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="excluirParametro(${item.id}, '${item.chave}')" title="Excluir">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ==========================================================================
// CUSTO OPERACAO (PARAMETRO PRINCIPAL)
// ==========================================================================
function salvarCustoOperacao() {
    const percentual = parseFloat(document.getElementById('operacao-percentual').value);

    if (isNaN(percentual) || percentual < 0) {
        alert('Informe um percentual valido');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/parametros/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            chave: 'CUSTO_OPERACAO_PERCENTUAL',
            valor: percentual,
            descricao: 'Percentual de custo operacional aplicado sobre preco de venda'
        })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            alert('Custo de operacao salvo com sucesso!');
            carregarParametros();
            carregarCustoOperacao();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao salvar');
    });
}

// ==========================================================================
// CUSTO FINANCEIRO (PARAMETRO PRINCIPAL)
// ==========================================================================
function salvarCustoFinanceiro() {
    const percentual = parseFloat(document.getElementById('financeiro-percentual').value);

    if (isNaN(percentual) || percentual < 0) {
        alert('Informe um percentual valido');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/parametros/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            chave: 'CUSTO_FINANCEIRO_PERCENTUAL',
            valor: percentual,
            descricao: 'Percentual de custo financeiro aplicado sobre preco de venda (juros, taxas)'
        })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            alert('Custo financeiro salvo com sucesso!');
            carregarParametros();
            carregarCustoFinanceiro();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao salvar');
    });
}

// ==========================================================================
// CRUD PARAMETROS
// ==========================================================================
function abrirModalParametro() {
    document.getElementById('parametro-id').value = '';
    document.getElementById('parametro-chave').value = '';
    document.getElementById('parametro-valor').value = '';
    document.getElementById('parametro-descricao').value = '';
    document.getElementById('parametro-chave').disabled = false;

    new bootstrap.Modal(document.getElementById('modalParametro')).show();
}

function editarParametro(id) {
    const param = dadosParametros.find(p => p.id === id);
    if (!param) return;

    document.getElementById('parametro-id').value = param.id;
    document.getElementById('parametro-chave').value = param.chave;
    document.getElementById('parametro-valor').value = param.valor;
    document.getElementById('parametro-descricao').value = param.descricao || '';
    document.getElementById('parametro-chave').disabled = true;

    new bootstrap.Modal(document.getElementById('modalParametro')).show();
}

function salvarParametro() {
    const id = document.getElementById('parametro-id').value;
    const chave = document.getElementById('parametro-chave').value.trim().toUpperCase();
    const valor = parseFloat(document.getElementById('parametro-valor').value);
    const descricao = document.getElementById('parametro-descricao').value.trim();

    if (!chave) {
        alert('Informe a chave do parametro');
        return;
    }

    if (isNaN(valor)) {
        alert('Informe um valor valido');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/parametros/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            id: id || null,
            chave,
            valor,
            descricao
        })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalParametro')).hide();
            carregarParametros();
            carregarCustoOperacao();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao salvar');
    });
}

function excluirParametro(id, chave) {
    if (!confirm(`Deseja excluir o parametro "${chave}"?`)) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch(`/custeio/api/parametros/excluir/${id}`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            carregarParametros();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao excluir');
    });
}

// ==========================================================================
// IMPORTAR
// ==========================================================================
function importarParametros(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/parametros/importar', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        input.value = '';

        if (data.sucesso) {
            alert(data.mensagem);
            carregarParametros();
            carregarCustoOperacao();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        input.value = '';
        console.error(err);
        alert('Erro ao importar');
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
