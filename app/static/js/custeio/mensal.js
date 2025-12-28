/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Fechamento Mensal JavaScript
 * Com expansão inline BOM
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosMensal = [];
let expandidos = new Set(); // Rastreia produtos expandidos

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    // Definir mes/ano atual
    const hoje = new Date();
    document.getElementById('filtro-mes').value = hoje.getMonth() + 1;
    document.getElementById('filtro-ano').value = hoje.getFullYear();
});

// ==========================================================================
// CARREGAR DADOS
// ==========================================================================
function carregarDados() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;
    const tipo = document.getElementById('filtro-tipo').value;
    mostrarLoading(true);
    expandidos.clear(); // Limpar expandidos ao recarregar

    fetch(`/custeio/api/mensal/listar?mes=${mes}&ano=${ano}&tipo=${tipo}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosMensal = data.dados;
                atualizarEstatisticas(data);
                filtrarLocal();
            } else {
                alert('Erro: ' + (data.erro || 'Erro desconhecido'));
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
            alert('Erro ao carregar dados');
        });
}

function atualizarEstatisticas(data) {
    document.getElementById('stat-comprados').textContent = data.comprados || 0;
    document.getElementById('stat-intermediarios').textContent = data.intermediarios || 0;
    document.getElementById('stat-acabados').textContent = data.acabados || 0;
    document.getElementById('stat-status').textContent = data.status_periodo || 'ABERTO';
}

// ==========================================================================
// FILTROS E RENDERIZACAO
// ==========================================================================
function filtrarLocal() {
    const termo = document.getElementById('filtro-busca').value.toLowerCase();

    let dadosFiltrados = dadosMensal;

    if (termo) {
        dadosFiltrados = dadosFiltrados.filter(d =>
            d.cod_produto.toLowerCase().includes(termo) ||
            (d.nome_produto && d.nome_produto.toLowerCase().includes(termo))
        );
    }

    renderizarTabela(dadosFiltrados);
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-mensal');
    document.getElementById('total-registros').textContent = `${dados.length} produto(s)`;

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum produto encontrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => {
        const podeExpandir = item.tipo_produto !== 'COMPRADO';
        const estaExpandido = expandidos.has(item.cod_produto);

        // Badge de tipo
        let tipoBadge = '';
        if (item.tipo_produto === 'COMPRADO') {
            tipoBadge = '<span class="badge bg-primary">COMPRADO</span>';
        } else if (item.tipo_produto === 'ACABADO') {
            tipoBadge = '<span class="badge bg-success">ACABADO</span>';
        } else if (item.tipo_produto === 'INTERMEDIARIO') {
            tipoBadge = '<span class="badge bg-warning text-dark">INTERMEDIÁRIO</span>';
        }

        // Formatar valores
        const qtdEstoqueInicial = formatarNumero(item.qtd_estoque_inicial, 0);
        const custoInicial = formatarMoeda(item.custo_estoque_inicial);
        const qtdComprada = formatarNumero(item.qtd_comprada || item.qtd_produzida, 0);
        const custoCompras = formatarMoeda(item.valor_compras_liquido || item.custo_producao);
        const custoMedio = formatarMoeda(item.custo_medio_estoque || item.custo_bom);
        const qtdEstoqueFinal = formatarNumero(item.qtd_estoque_final, 0);

        // Ícone de expansão
        const iconExpand = podeExpandir
            ? `<i class="bi ${estaExpandido ? 'bi-chevron-down' : 'bi-chevron-right'} expand-icon"></i>`
            : '';

        // Classe da linha
        const rowClass = podeExpandir ? 'row-expandable' : '';
        const clickHandler = podeExpandir
            ? `onclick="toggleExpansao('${item.cod_produto}')"`
            : '';

        return `
            <tr class="${rowClass}" ${clickHandler} data-cod="${item.cod_produto}">
                <td class="text-center" style="width: 30px;">${iconExpand}</td>
                <td><code>${item.cod_produto}</code></td>
                <td>${item.nome_produto || '-'}</td>
                <td class="text-center">${tipoBadge}</td>
                <td class="text-end">${qtdEstoqueInicial}</td>
                <td class="text-end valor-custo">${custoInicial}</td>
                <td class="text-end">${qtdComprada}</td>
                <td class="text-end valor-custo">${custoCompras}</td>
                <td class="text-end valor-custo custo-destacado">${custoMedio}</td>
                <td class="text-end">${qtdEstoqueFinal}</td>
            </tr>
        `;
    }).join('');
}

// ==========================================================================
// EXPANSAO INLINE BOM
// ==========================================================================
function toggleExpansao(codProduto) {
    const tbody = document.getElementById('tbody-mensal');
    const rowPai = tbody.querySelector(`tr[data-cod="${codProduto}"]`);

    if (!rowPai) return;

    if (expandidos.has(codProduto)) {
        // Fechar: remover linhas de componentes
        colapsarComponentes(codProduto);
        expandidos.delete(codProduto);

        // Atualizar ícone
        const icon = rowPai.querySelector('.expand-icon');
        if (icon) {
            icon.classList.remove('bi-chevron-down');
            icon.classList.add('bi-chevron-right');
        }
    } else {
        // Expandir: buscar e mostrar componentes
        expandirComponentes(codProduto, rowPai);
        expandidos.add(codProduto);

        // Atualizar ícone
        const icon = rowPai.querySelector('.expand-icon');
        if (icon) {
            icon.classList.remove('bi-chevron-right');
            icon.classList.add('bi-chevron-down');
        }
    }
}

function expandirComponentes(codProduto, rowPai) {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    // Mostrar loading na linha
    const loadingRow = document.createElement('tr');
    loadingRow.className = 'bom-row';
    loadingRow.dataset.parent = codProduto;
    loadingRow.innerHTML = `
        <td></td>
        <td colspan="9" class="text-center py-2">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <span class="ms-2">Carregando componentes...</span>
        </td>
    `;
    rowPai.after(loadingRow);

    fetch(`/custeio/api/mensal/detalhe-bom/${codProduto}?mes=${mes}&ano=${ano}`)
        .then(r => r.json())
        .then(data => {
            // Remover linha de loading
            loadingRow.remove();

            if (!data.sucesso) {
                console.error(data.erro);
                return;
            }

            if (!data.componentes || data.componentes.length === 0) {
                const emptyRow = document.createElement('tr');
                emptyRow.className = 'bom-row';
                emptyRow.dataset.parent = codProduto;
                emptyRow.innerHTML = `
                    <td></td>
                    <td colspan="9" class="text-muted small py-1 ps-4">
                        <i class="bi bi-info-circle me-1"></i>Sem componentes BOM cadastrados
                    </td>
                `;
                rowPai.after(emptyRow);
                return;
            }

            // Inserir componentes em ordem reversa para manter a ordem correta
            const componentes = data.componentes.reverse();

            for (const comp of componentes) {
                const compRow = criarLinhaComponente(codProduto, comp);
                rowPai.after(compRow);
            }

            // Linha de total
            const totalRow = document.createElement('tr');
            totalRow.className = 'bom-row bom-total';
            totalRow.dataset.parent = codProduto;
            totalRow.innerHTML = `
                <td></td>
                <td colspan="7" class="text-end small fw-bold text-muted pe-2">
                    Custo BOM Total:
                </td>
                <td class="text-end valor-custo fw-bold">
                    ${formatarMoeda(data.custo_bom_calculado)}
                </td>
                <td></td>
            `;
            rowPai.after(totalRow);
        })
        .catch(err => {
            loadingRow.remove();
            console.error(err);
        });
}

function criarLinhaComponente(codPai, comp) {
    const row = document.createElement('tr');
    row.className = 'bom-row';
    row.dataset.parent = codPai;

    // Badge de tipo do componente
    let tipoBadge = '';
    if (comp.tipo === 'COMPRADO' || comp.tipo === 'COMPONENTE') {
        tipoBadge = '<span class="badge bg-primary badge-sm">COMP</span>';
    } else if (comp.tipo === 'INTERMEDIARIO') {
        tipoBadge = '<span class="badge bg-warning text-dark badge-sm">INTERM</span>';
    }

    // Indicador de nível (indentação)
    const indent = '└─ ';

    row.innerHTML = `
        <td></td>
        <td class="ps-4 text-muted small">
            ${indent}<code>${comp.cod_produto}</code>
        </td>
        <td class="small">${comp.nome_produto || '-'}</td>
        <td class="text-center">${tipoBadge}</td>
        <td></td>
        <td></td>
        <td class="text-end small">${formatarNumero(comp.qtd_utilizada, 4)}</td>
        <td class="text-end small valor-custo">${formatarMoeda(comp.custo_unitario)}</td>
        <td class="text-end small valor-custo">${formatarMoeda(comp.custo_total)}</td>
        <td></td>
    `;

    return row;
}

function colapsarComponentes(codProduto) {
    const tbody = document.getElementById('tbody-mensal');
    const rowsToRemove = tbody.querySelectorAll(`tr.bom-row[data-parent="${codProduto}"]`);
    rowsToRemove.forEach(row => row.remove());
}

// ==========================================================================
// FORMATADORES
// ==========================================================================
function formatarNumero(valor, decimais = 0) {
    if (valor === null || valor === undefined) return '-';
    return Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: decimais,
        maximumFractionDigits: decimais
    });
}

function formatarMoeda(valor) {
    if (valor === null || valor === undefined) return '-';
    return `R$ ${Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

// ==========================================================================
// SIMULACAO E FECHAMENTO
// ==========================================================================
function simularFechamento() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;
    mostrarLoading(true);

    fetch(`/custeio/api/mensal/simular?mes=${mes}&ano=${ano}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                mostrarPreview(data);
            } else {
                alert('Erro: ' + (data.erro || 'Erro desconhecido'));
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
            alert('Erro ao simular fechamento');
        });
}

function mostrarPreview(data) {
    const meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    let html = `
        <div class="alert alert-info">
            <strong>Preview do Fechamento - ${meses[mes]}/${ano}</strong>
        </div>
        <div class="row mb-3">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body py-2">
                        <h5 class="mb-0">${data.comprados || 0}</h5>
                        <small class="text-muted">Comprados</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body py-2">
                        <h5 class="mb-0">${data.intermediarios || 0}</h5>
                        <small class="text-muted">Intermediários</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body py-2">
                        <h5 class="mb-0">${data.acabados || 0}</h5>
                        <small class="text-muted">Acabados</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body py-2">
                        <h5 class="mb-0">${data.total || 0}</h5>
                        <small class="text-muted">Total</small>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (data.preview && data.preview.length > 0) {
        html += `
            <div class="table-responsive" style="max-height: 400px;">
                <table class="table table-sm">
                    <thead class="sticky-top bg-white">
                        <tr>
                            <th>Código</th>
                            <th>Nome</th>
                            <th>Tipo</th>
                            <th class="text-end">Custo Calculado</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.preview.map(p => `
                            <tr>
                                <td><code>${p.cod_produto}</code></td>
                                <td>${p.nome_produto || '-'}</td>
                                <td>${p.tipo_produto}</td>
                                <td class="text-end">R$ ${(p.custo_calculado || 0).toFixed(2)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    document.getElementById('preview-content').innerHTML = html;
    new bootstrap.Modal(document.getElementById('modalPreview')).show();
}

function confirmarFechamento() {
    const meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    document.getElementById('fechamento-periodo').textContent = `${meses[mes]}/${ano}`;

    // Fechar preview se estiver aberto
    const modalPreview = bootstrap.Modal.getInstance(document.getElementById('modalPreview'));
    if (modalPreview) modalPreview.hide();

    new bootstrap.Modal(document.getElementById('modalFechamento')).show();
}

function executarFechamento() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);
    bootstrap.Modal.getInstance(document.getElementById('modalFechamento')).hide();

    fetch('/custeio/api/mensal/fechar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ mes, ano })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            alert(data.mensagem || 'Fechamento realizado com sucesso!');
            carregarDados();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao executar fechamento');
    });
}

// ==========================================================================
// EXPORTAR
// ==========================================================================
function exportarMensal() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;
    window.location.href = `/custeio/api/mensal/exportar?mes=${mes}&ano=${ano}`;
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
