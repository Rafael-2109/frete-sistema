/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Custo de Frete JavaScript
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosFrete = [];
const UFS_BRASIL = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    popularSelectUFs();
    carregarDados();
});

function popularSelectUFs() {
    const selects = ['filtro-uf', 'frete-uf'];
    selects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            UFS_BRASIL.forEach(uf => {
                const option = document.createElement('option');
                option.value = uf;
                option.textContent = uf;
                select.appendChild(option);
            });
        }
    });
}

// ==========================================================================
// CARREGAR DADOS
// ==========================================================================
function carregarDados() {
    const apenasVigentes = document.getElementById('filtro-vigentes').checked;
    mostrarLoading(true);

    fetch(`/custeio/api/frete/listar?apenas_vigentes=${apenasVigentes}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosFrete = data.dados;
                aplicarFiltros();
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
            alert('Erro ao carregar dados');
        });
}

// ==========================================================================
// FILTROS E RENDERIZACAO
// ==========================================================================
function aplicarFiltros() {
    const incoterm = document.getElementById('filtro-incoterm').value;
    const uf = document.getElementById('filtro-uf').value;

    let dadosFiltrados = dadosFrete;

    if (incoterm) {
        dadosFiltrados = dadosFiltrados.filter(d => d.incoterm === incoterm);
    }
    if (uf) {
        dadosFiltrados = dadosFiltrados.filter(d => d.cod_uf === uf);
    }

    renderizarTabela(dadosFiltrados);
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-frete');
    document.getElementById('total-registros').textContent = `${dados.length} registro(s)`;

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum registro encontrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => `
        <tr>
            <td><span class="badge bg-info">${item.incoterm}</span></td>
            <td><span class="badge bg-secondary">${item.cod_uf}</span></td>
            <td class="text-end valor-custo"><strong>${item.percentual_frete.toFixed(2)}%</strong></td>
            <td>${item.vigencia_inicio || '-'}</td>
            <td>${item.vigencia_fim || '<span class="text-success">Vigente</span>'}</td>
            <td>${item.criado_por || '-'}</td>
            <td class="text-center">
                <button class="btn btn-outline-primary btn-sm" onclick="editarFrete(${item.id})" title="Editar">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="excluirFrete(${item.id})" title="Excluir">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// ==========================================================================
// CRUD OPERATIONS
// ==========================================================================
function abrirModalFrete() {
    document.getElementById('frete-id').value = '';
    document.getElementById('frete-incoterm').value = '';
    document.getElementById('frete-uf').value = '';
    document.getElementById('frete-percentual').value = '';
    document.getElementById('frete-vigencia-inicio').value = new Date().toISOString().split('T')[0];
    document.getElementById('frete-vigencia-fim').value = '';

    new bootstrap.Modal(document.getElementById('modalFrete')).show();
}

function editarFrete(id) {
    const item = dadosFrete.find(f => f.id === id);
    if (!item) return;

    document.getElementById('frete-id').value = item.id;
    document.getElementById('frete-incoterm').value = item.incoterm;
    document.getElementById('frete-uf').value = item.cod_uf;
    document.getElementById('frete-percentual').value = item.percentual_frete;
    document.getElementById('frete-vigencia-inicio').value = item.vigencia_inicio || '';
    document.getElementById('frete-vigencia-fim').value = item.vigencia_fim || '';

    new bootstrap.Modal(document.getElementById('modalFrete')).show();
}

function salvarFrete() {
    const id = document.getElementById('frete-id').value;
    const incoterm = document.getElementById('frete-incoterm').value;
    const cod_uf = document.getElementById('frete-uf').value;
    const percentual_frete = parseFloat(document.getElementById('frete-percentual').value);
    const vigencia_inicio = document.getElementById('frete-vigencia-inicio').value;
    const vigencia_fim = document.getElementById('frete-vigencia-fim').value;

    if (!incoterm || !cod_uf || isNaN(percentual_frete)) {
        alert('Preencha todos os campos obrigatorios');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/frete/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            id: id || null,
            incoterm,
            cod_uf,
            percentual_frete,
            vigencia_inicio,
            vigencia_fim: vigencia_fim || null
        })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalFrete')).hide();
            alert('Registro salvo com sucesso!');
            carregarDados();
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

function excluirFrete(id) {
    if (!confirm('Deseja excluir este registro?')) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch(`/custeio/api/frete/excluir/${id}`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            alert('Registro excluido com sucesso!');
            carregarDados();
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
// IMPORT/EXPORT
// ==========================================================================
function exportarFrete() {
    window.location.href = '/custeio/api/frete/exportar';
}

function baixarModelo() {
    window.location.href = '/custeio/api/frete/modelo';
}

function importarFrete(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/frete/importar', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        input.value = '';

        if (data.sucesso) {
            let msg = data.mensagem;
            if (data.erros && data.erros.length > 0) {
                msg += '\n\nErros:\n' + data.erros.slice(0, 5).join('\n');
            }
            alert(msg);
            carregarDados();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        input.value = '';
        console.error(err);
        alert('Erro ao importar arquivo');
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
