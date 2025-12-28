/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Composicao de Custo JavaScript
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosComposicao = [];

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
    const termo = document.getElementById('filtro-busca').value;
    mostrarLoading(true);

    fetch(`/custeio/api/composicao/listar?tipo=${tipo}&termo=${termo}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosComposicao = data.dados;
                filtrarLocal();
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
    const apenasBOM = document.getElementById('filtro-com-bom').checked;

    let dadosFiltrados = dadosComposicao;

    if (termo) {
        dadosFiltrados = dadosFiltrados.filter(d =>
            d.cod_produto.toLowerCase().includes(termo) ||
            (d.nome_produto && d.nome_produto.toLowerCase().includes(termo))
        );
    }

    if (apenasBOM) {
        dadosFiltrados = dadosFiltrados.filter(d => d.tem_bom);
    }

    renderizarTabela(dadosFiltrados);
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-composicao');
    document.getElementById('total-registros').textContent = `${dados.length} produto(s)`;

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum produto encontrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => {
        let tipoBadge = '';
        if (item.tipo === 'COMPRADO') {
            tipoBadge = '<span class="badge bg-primary">COMPRADO</span>';
        } else if (item.tipo === 'ACABADO') {
            tipoBadge = '<span class="badge bg-success">ACABADO</span>';
        } else {
            tipoBadge = '<span class="badge bg-warning text-dark">INTERMEDIARIO</span>';
        }

        const expandBtn = item.tem_bom
            ? `<button class="btn btn-link btn-sm p-0" onclick="verDetalhesBOM('${item.cod_produto}', '${item.nome_produto}')">
                 <i class="bi bi-chevron-right"></i>
               </button>`
            : '';

        const qtdComp = item.tem_bom
            ? `<span class="badge bg-info">${item.componentes.length}</span>`
            : '<span class="text-muted">-</span>';

        const custoBOM = item.custo_bom !== null && item.tem_bom
            ? `R$ ${item.custo_bom.toFixed(2)}`
            : '-';

        const custoConsiderado = item.custo_considerado !== null
            ? `R$ ${item.custo_considerado.toFixed(2)}`
            : '-';

        return `
            <tr>
                <td class="text-center">${expandBtn}</td>
                <td><code>${item.cod_produto}</code></td>
                <td>${item.nome_produto || '-'}</td>
                <td class="text-center">${tipoBadge}</td>
                <td class="text-center">${qtdComp}</td>
                <td class="text-end valor-custo">${custoBOM}</td>
                <td class="text-end valor-custo">${custoConsiderado}</td>
            </tr>
        `;
    }).join('');
}

// ==========================================================================
// DETALHES BOM
// ==========================================================================
function verDetalhesBOM(codProduto, nomeProduto) {
    document.getElementById('modal-produto-cod').textContent = codProduto;
    document.getElementById('modal-produto-nome').textContent = nomeProduto;

    // Buscar nos dados locais
    const produto = dadosComposicao.find(p => p.cod_produto === codProduto);

    if (!produto || !produto.componentes) {
        document.getElementById('tbody-bom-detalhe').innerHTML = '<tr><td colspan="6" class="text-center">Sem componentes</td></tr>';
        document.getElementById('total-custo-bom').textContent = '-';
    } else {
        let totalBOM = 0;

        document.getElementById('tbody-bom-detalhe').innerHTML = produto.componentes.map(comp => {
            const custoUnit = comp.custo_componente !== null ? comp.custo_componente : 0;
            const custoTotal = custoUnit * comp.qtd_utilizada;
            totalBOM += custoTotal;

            const tipoBadge = comp.cod_componente && comp.cod_componente.startsWith('MP')
                ? '<span class="badge bg-primary">MP</span>'
                : '<span class="badge bg-secondary">SEMI</span>';

            return `
                <tr>
                    <td><code>${comp.cod_componente}</code></td>
                    <td>${comp.nome_componente || '-'}</td>
                    <td class="text-center">${tipoBadge}</td>
                    <td class="text-end">${comp.qtd_utilizada.toFixed(4)}</td>
                    <td class="text-end">${custoUnit > 0 ? 'R$ ' + custoUnit.toFixed(2) : '-'}</td>
                    <td class="text-end">${custoTotal > 0 ? 'R$ ' + custoTotal.toFixed(2) : '-'}</td>
                </tr>
            `;
        }).join('');

        document.getElementById('total-custo-bom').textContent = totalBOM > 0 ? `R$ ${totalBOM.toFixed(2)}` : '-';
    }

    new bootstrap.Modal(document.getElementById('modalBOM')).show();
}

// ==========================================================================
// EXPORT
// ==========================================================================
function exportarComposicao() {
    const tipo = document.getElementById('filtro-tipo').value;
    window.location.href = `/custeio/api/composicao/exportar?tipo=${tipo}`;
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
