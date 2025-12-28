/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Custo de Producao JavaScript
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosProducao = [];

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    carregarDados();
});

// ==========================================================================
// CARREGAR DADOS
// ==========================================================================
function carregarDados() {
    const tipo = document.getElementById('filtro-tipo').value;
    mostrarLoading(true);

    fetch(`/custeio/api/producao/listar?tipo=${tipo}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosProducao = data.dados;
                renderizarTabela(dadosProducao);
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
function filtrarLocal() {
    const termo = document.getElementById('filtro-busca').value.toLowerCase();

    let dadosFiltrados = dadosProducao;

    if (termo) {
        dadosFiltrados = dadosFiltrados.filter(d =>
            d.cod_produto.toLowerCase().includes(termo) ||
            (d.nome_produto && d.nome_produto.toLowerCase().includes(termo))
        );
    }

    renderizarTabela(dadosFiltrados);
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-producao');
    document.getElementById('total-registros').textContent = `${dados.length} produto(s)`;

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum produto produzido encontrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => {
        const tipoBadge = item.tipo === 'ACABADO'
            ? '<span class="badge bg-success">ACABADO</span>'
            : '<span class="badge bg-warning text-dark">INTERMEDIARIO</span>';

        const linhasHtml = item.linhas_producao.length > 0
            ? item.linhas_producao.map(l => `
                <span class="linha-producao-badge">${l.linha}</span>
                <small class="capacidade-info">${l.capacidade ? l.capacidade.toFixed(1) + ' un/min' : ''}</small>
            `).join(' ')
            : '<span class="text-muted">-</span>';

        const custoConsiderado = item.custo_considerado !== null
            ? `R$ ${item.custo_considerado.toFixed(2)}`
            : '-';

        // Campo editavel para custo de producao
        const custoProducaoValue = item.custo_producao !== null ? item.custo_producao.toFixed(2) : '';
        const custoProducaoInput = `
            <input type="number"
                   class="editable-input"
                   data-cod-produto="${item.cod_produto}"
                   data-original="${custoProducaoValue}"
                   value="${custoProducaoValue}"
                   step="0.01"
                   min="0"
                   placeholder="0.00"
                   onblur="salvarCustoProducao(this)"
                   onkeydown="if(event.key==='Enter'){this.blur();}">
        `;

        // Versao e atualizacao
        const versao = item.versao ? `v${item.versao}` : '-';
        const atualizado = item.atualizado_em
            ? `<small>${item.atualizado_em}</small><br><small class="text-muted">${item.atualizado_por || ''}</small>`
            : '-';

        return `
            <tr>
                <td><code>${item.cod_produto}</code></td>
                <td>${item.nome_produto || '-'}</td>
                <td class="text-center">${tipoBadge}</td>
                <td>${linhasHtml}</td>
                <td class="text-end valor-custo">${custoConsiderado}</td>
                <td class="text-end" style="background-color: var(--bs-warning-bg-subtle);">${custoProducaoInput}</td>
                <td class="text-center"><span class="badge bg-secondary">${versao}</span></td>
                <td>${atualizado}</td>
            </tr>
        `;
    }).join('');
}

// ==========================================================================
// SALVAR CUSTO PRODUCAO (EDICAO INLINE)
// ==========================================================================
function salvarCustoProducao(input) {
    const codProduto = input.dataset.codProduto;
    const valorOriginal = input.dataset.original;
    const valorNovo = input.value.trim();

    // Se nao mudou, nao faz nada
    if (valorNovo === valorOriginal) {
        return;
    }

    // Validar valor
    const valor = parseFloat(valorNovo);
    if (valorNovo !== '' && (isNaN(valor) || valor < 0)) {
        alert('Valor invalido');
        input.value = valorOriginal;
        return;
    }

    // Mostrar estado de loading no input
    input.classList.add('is-loading');

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/producao/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            cod_produto: codProduto,
            custo_producao: valorNovo !== '' ? valor : null
        })
    })
    .then(r => r.json())
    .then(data => {
        input.classList.remove('is-loading');
        if (data.sucesso) {
            // Mostrar sucesso temporario
            input.classList.add('is-valid');
            input.dataset.original = valorNovo;
            setTimeout(() => {
                input.classList.remove('is-valid');
            }, 2000);

            // Atualizar dados locais
            const item = dadosProducao.find(d => d.cod_produto === codProduto);
            if (item) {
                item.custo_producao = valorNovo !== '' ? valor : null;
                item.versao = (item.versao || 0) + 1;
                item.atualizado_em = new Date().toLocaleString('pt-BR');
            }
        } else {
            input.classList.add('is-invalid');
            setTimeout(() => {
                input.classList.remove('is-invalid');
                input.value = valorOriginal;
            }, 2000);
            alert('Erro: ' + (data.erro || 'Erro ao salvar'));
        }
    })
    .catch(err => {
        input.classList.remove('is-loading');
        input.classList.add('is-invalid');
        setTimeout(() => {
            input.classList.remove('is-invalid');
            input.value = valorOriginal;
        }, 2000);
        console.error(err);
        alert('Erro ao salvar custo');
    });
}

// ==========================================================================
// IMPORT/EXPORT
// ==========================================================================
function exportarProducao() {
    window.location.href = '/custeio/api/producao/exportar';
}

function baixarModelo() {
    window.location.href = '/custeio/api/producao/modelo';
}

function importarProducao(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/producao/importar', {
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
