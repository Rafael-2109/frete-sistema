/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - Definicao de Custo JavaScript
 * Com expansão inline de detalhes BOM
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosDefinicao = [];
let salvandoCusto = false;
let expandidos = new Map(); // cod_produto -> Set de tipos expandidos
let colunasExpandidas = new Set(); // Colunas com todos expandidos

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

    // Limpar expansões ao recarregar
    expandidos.clear();
    colunasExpandidas.clear();
    atualizarIconesCabecalho();

    fetch(`/custeio/api/definicao/listar?tipo=${tipo}&termo=${termo}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosDefinicao = data.dados;
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
    const apenasComCusto = document.getElementById('filtro-com-custo').checked;

    let dadosFiltrados = dadosDefinicao;

    if (termo) {
        dadosFiltrados = dadosFiltrados.filter(d =>
            d.cod_produto.toLowerCase().includes(termo) ||
            (d.nome_produto && d.nome_produto.toLowerCase().includes(termo))
        );
    }

    if (apenasComCusto) {
        dadosFiltrados = dadosFiltrados.filter(d => d.custo_considerado !== null);
    }

    renderizarTabela(dadosFiltrados);
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-definicao');
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
        } else if (item.tipo === 'INTERMEDIARIO') {
            tipoBadge = '<span class="badge bg-warning text-dark">INTERMEDIÁRIO</span>';
        } else {
            tipoBadge = '<span class="badge bg-secondary">OUTRO</span>';
        }

        // Formatar valores
        const medioMes = formatarMoeda(item.custo_medio_mes);
        const ultimoCusto = formatarMoeda(item.ultimo_custo);
        const medioEstoque = formatarMoeda(item.custo_medio_estoque);
        const custoConsideradoValue = item.custo_considerado !== null ? item.custo_considerado.toFixed(2) : '';

        // Verificar se produto é produzido (pode expandir BOM)
        const eProduzido = item.tipo !== 'COMPRADO';

        // Criar células - clicáveis apenas para produtos produzidos
        const celulaMedioMes = criarCelulaExpandivel(item, 'medio_mes', medioMes, eProduzido);
        const celulaUltimoCusto = criarCelulaExpandivel(item, 'ultimo_custo', ultimoCusto, eProduzido);
        const celulaMedioEstoque = criarCelulaExpandivel(item, 'medio_estoque', medioEstoque, eProduzido);

        // Produtos produzidos não podem ter custo editado diretamente
        // O custo é calculado via BOM
        let celulaCustoConsiderado;
        if (eProduzido) {
            // Produto PRODUZIDO - não editável, mas clicável para ver BOM
            const expandidosItem = expandidos.get(item.cod_produto) || new Set();
            const estaExpandido = expandidosItem.has('custo_considerado');
            const iconClass = estaExpandido ? 'bi-chevron-down' : 'bi-chevron-right';
            const custoFormatado = custoConsideradoValue ? formatarMoeda(parseFloat(custoConsideradoValue)) : '-';

            celulaCustoConsiderado = `
                <td class="text-end valor-expandivel ${estaExpandido ? 'expanded' : ''}"
                    style="background-color: var(--bs-success-bg-subtle); cursor: pointer;"
                    data-cod="${item.cod_produto}"
                    data-tipo="custo_considerado"
                    onclick="toggleExpand('${item.cod_produto}', 'custo_considerado')"
                    title="Clique para ver lista de materiais">
                    ${custoFormatado}
                    <i class="bi ${iconClass} expand-icon ms-1" style="font-size: 0.7rem;"></i>
                </td>
            `;
        } else {
            // Produto COMPRADO - editável
            celulaCustoConsiderado = `
                <td class="text-end" style="background-color: var(--bs-success-bg-subtle);">
                    <input type="number"
                           class="form-control form-control-sm editable-input text-end"
                           value="${custoConsideradoValue}"
                           step="0.01"
                           min="0"
                           data-cod-produto="${item.cod_produto}"
                           onchange="salvarCusto(this)"
                           onkeydown="handleEnterKey(event, this)"
                           placeholder="0.00">
                </td>
            `;
        }

        return `
            <tr data-cod="${item.cod_produto}" data-tipo="${item.tipo}">
                <td><code>${item.cod_produto}</code></td>
                <td>${item.nome_produto || '-'}</td>
                <td class="text-center">${tipoBadge}</td>
                ${celulaMedioMes}
                ${celulaUltimoCusto}
                ${celulaMedioEstoque}
                ${celulaCustoConsiderado}
            </tr>
        `;
    }).join('');
}

function criarCelulaExpandivel(item, tipo, valorFormatado, clicavel) {
    if (!clicavel) {
        // Produto COMPRADO - não expande
        return `<td class="text-end text-muted">${valorFormatado}</td>`;
    }

    const expandidosItem = expandidos.get(item.cod_produto) || new Set();
    const estaExpandido = expandidosItem.has(tipo);
    const iconClass = estaExpandido ? 'bi-chevron-down' : 'bi-chevron-right';

    return `
        <td class="text-end text-muted valor-expandivel ${estaExpandido ? 'expanded' : ''}"
            data-cod="${item.cod_produto}"
            data-tipo="${tipo}"
            onclick="toggleExpand('${item.cod_produto}', '${tipo}')">
            ${valorFormatado}
            <i class="bi ${iconClass} expand-icon ms-1" style="font-size: 0.7rem;"></i>
        </td>
    `;
}

// ==========================================================================
// EXPANSAO INLINE
// ==========================================================================
function toggleExpand(codProduto, tipoValor) {
    const tbody = document.getElementById('tbody-definicao');
    const rowPai = tbody.querySelector(`tr[data-cod="${codProduto}"]`);
    if (!rowPai) return;

    // Inicializar set se não existir
    if (!expandidos.has(codProduto)) {
        expandidos.set(codProduto, new Set());
    }

    const expandidosItem = expandidos.get(codProduto);

    if (expandidosItem.has(tipoValor)) {
        // Colapsar
        colapsarDetalhe(codProduto, tipoValor);
        expandidosItem.delete(tipoValor);

        // Atualizar ícone da célula
        const celula = rowPai.querySelector(`td[data-tipo="${tipoValor}"]`);
        if (celula) {
            celula.classList.remove('expanded');
            const icon = celula.querySelector('.expand-icon');
            if (icon) {
                icon.classList.remove('bi-chevron-down');
                icon.classList.add('bi-chevron-right');
            }
        }
    } else {
        // Expandir
        expandirDetalhe(codProduto, rowPai, tipoValor);
        expandidosItem.add(tipoValor);

        // Atualizar ícone da célula
        const celula = rowPai.querySelector(`td[data-tipo="${tipoValor}"]`);
        if (celula) {
            celula.classList.add('expanded');
            const icon = celula.querySelector('.expand-icon');
            if (icon) {
                icon.classList.remove('bi-chevron-right');
                icon.classList.add('bi-chevron-down');
            }
        }
    }
}

function expandirDetalhe(codProduto, rowPai, tipoValor) {
    // Mostrar loading
    const loadingRow = document.createElement('tr');
    loadingRow.className = 'detail-row';
    loadingRow.dataset.parent = codProduto;
    loadingRow.dataset.tipo = tipoValor;
    loadingRow.innerHTML = `
        <td></td>
        <td colspan="6" class="text-center py-2">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <span class="ms-2 text-muted">Carregando composição BOM...</span>
        </td>
    `;
    rowPai.after(loadingRow);

    // Buscar composição BOM com custos calculados pelo critério selecionado
    fetch(`/custeio/api/definicao/bom/${codProduto}?criterio=${tipoValor}`)
        .then(r => r.json())
        .then(data => {
            loadingRow.remove();

            if (!data.sucesso || !data.componentes || data.componentes.length === 0) {
                const emptyRow = criarLinhaDetalheVazia(codProduto, tipoValor, 'Sem componentes BOM');
                rowPai.after(emptyRow);
                return;
            }

            // Criar linhas de componentes (em ordem reversa para inserir corretamente)
            const componentes = data.componentes.slice().reverse();
            for (const comp of componentes) {
                const compRow = criarLinhaComponenteBOM(codProduto, tipoValor, comp);
                rowPai.after(compRow);
            }

            // Linha de total
            const totalRow = criarLinhaTotalBOM(codProduto, tipoValor, data.custo_total);
            rowPai.after(totalRow);
        })
        .catch(err => {
            loadingRow.remove();
            console.error(err);
            const errorRow = criarLinhaDetalheVazia(codProduto, tipoValor, 'Erro ao carregar');
            rowPai.after(errorRow);
        });
}

function criarLinhaDetalheVazia(codProduto, tipoValor, mensagem) {
    const row = document.createElement('tr');
    row.className = 'detail-row';
    row.dataset.parent = codProduto;
    row.dataset.tipo = tipoValor;
    row.innerHTML = `
        <td></td>
        <td colspan="6" class="text-muted small py-1 ps-4">
            <i class="bi bi-info-circle me-1"></i>${mensagem}
        </td>
    `;
    return row;
}

function criarLinhaComponenteBOM(codProduto, tipoValor, comp) {
    const row = document.createElement('tr');
    row.className = 'detail-row bom-row';
    row.dataset.parent = codProduto;
    row.dataset.tipo = tipoValor;

    // Badge de tipo
    let tipoBadge = '';
    if (comp.tipo === 'COMPRADO' || comp.tipo === 'COMPONENTE') {
        tipoBadge = '<span class="badge bg-primary badge-sm">COMP</span>';
    } else if (comp.tipo === 'INTERMEDIARIO') {
        tipoBadge = '<span class="badge bg-warning text-dark badge-sm">INTERM</span>';
    }

    // Indentação baseada no nível
    const indent = '&nbsp;&nbsp;'.repeat(comp.nivel || 0);
    const prefixo = comp.nivel > 0 ? '└─' : '•';

    row.innerHTML = `
        <td></td>
        <td class="ps-3 text-muted small">
            ${indent}${prefixo} <code>${comp.cod_produto}</code>
        </td>
        <td class="small">${comp.nome_produto || '-'}</td>
        <td class="text-center">${tipoBadge}</td>
        <td class="text-end small">${formatarNumero(comp.qtd_utilizada, 4)}</td>
        <td class="text-end small valor-custo">${formatarMoeda(comp.custo_unitario)}</td>
        <td class="text-end small valor-custo fw-bold">${formatarMoeda(comp.custo_total)}</td>
    `;

    return row;
}

function criarLinhaTotalBOM(codProduto, tipoValor, custoTotal) {
    const row = document.createElement('tr');
    row.className = 'detail-row bom-total';
    row.dataset.parent = codProduto;
    row.dataset.tipo = tipoValor;
    row.innerHTML = `
        <td></td>
        <td colspan="5" class="text-end small fw-bold text-muted pe-2">
            Custo Total (${getNomeCriterio(tipoValor)}):
        </td>
        <td class="text-end valor-custo fw-bold custo-destacado">
            ${formatarMoeda(custoTotal)}
        </td>
    `;
    return row;
}

function getNomeCriterio(tipoValor) {
    switch (tipoValor) {
        case 'medio_mes': return 'Médio Mês';
        case 'ultimo_custo': return 'Último Custo';
        case 'medio_estoque': return 'Médio Estoque';
        case 'custo_considerado': return 'Custo Considerado';
        default: return tipoValor;
    }
}

function colapsarDetalhe(codProduto, tipoValor) {
    const tbody = document.getElementById('tbody-definicao');
    const rowsToRemove = tbody.querySelectorAll(`tr.detail-row[data-parent="${codProduto}"][data-tipo="${tipoValor}"]`);
    rowsToRemove.forEach(row => row.remove());
}

// ==========================================================================
// EXPANDIR/COLAPSAR TODOS (CABECALHO)
// ==========================================================================
function toggleAllExpand(tipoValor) {
    const header = document.querySelector(`th[data-col="${tipoValor}"]`);

    if (colunasExpandidas.has(tipoValor)) {
        // Colapsar todos
        colapsarTodos(tipoValor);
        colunasExpandidas.delete(tipoValor);
        if (header) header.classList.remove('expanded');
    } else {
        // Expandir todos
        expandirTodos(tipoValor);
        colunasExpandidas.add(tipoValor);
        if (header) header.classList.add('expanded');
    }
}

function expandirTodos(tipoValor) {
    const tbody = document.getElementById('tbody-definicao');
    const rows = tbody.querySelectorAll('tr[data-cod]');

    rows.forEach(row => {
        const codProduto = row.dataset.cod;
        const tipoProduto = row.dataset.tipo;

        // Só expandir se não for COMPRADO (comprados não tem BOM)
        if (tipoProduto === 'COMPRADO') {
            return;
        }

        // Inicializar set se não existir
        if (!expandidos.has(codProduto)) {
            expandidos.set(codProduto, new Set());
        }

        const expandidosItem = expandidos.get(codProduto);

        // Só expandir se não estiver expandido
        if (!expandidosItem.has(tipoValor)) {
            expandidosItem.add(tipoValor);
            expandirDetalhe(codProduto, row, tipoValor);

            // Atualizar ícone da célula
            const celula = row.querySelector(`td[data-tipo="${tipoValor}"]`);
            if (celula) {
                celula.classList.add('expanded');
                const icon = celula.querySelector('.expand-icon');
                if (icon) {
                    icon.classList.remove('bi-chevron-right');
                    icon.classList.add('bi-chevron-down');
                }
            }
        }
    });
}

function colapsarTodos(tipoValor) {
    const tbody = document.getElementById('tbody-definicao');

    // Remover todas as linhas de detalhe desse tipo
    const detailRows = tbody.querySelectorAll(`tr.detail-row[data-tipo="${tipoValor}"]`);
    detailRows.forEach(row => row.remove());

    // Atualizar estado e ícones
    expandidos.forEach((tiposExpandidos, codProduto) => {
        tiposExpandidos.delete(tipoValor);

        const rowPai = tbody.querySelector(`tr[data-cod="${codProduto}"]`);
        if (rowPai) {
            const celula = rowPai.querySelector(`td[data-tipo="${tipoValor}"]`);
            if (celula) {
                celula.classList.remove('expanded');
                const icon = celula.querySelector('.expand-icon');
                if (icon) {
                    icon.classList.remove('bi-chevron-down');
                    icon.classList.add('bi-chevron-right');
                }
            }
        }
    });
}

function atualizarIconesCabecalho() {
    const headers = document.querySelectorAll('.expandable-header');
    headers.forEach(header => {
        header.classList.remove('expanded');
    });
}

// ==========================================================================
// FORMATADORES
// ==========================================================================
function formatarMoeda(valor) {
    if (valor === null || valor === undefined) return '-';
    return `R$ ${Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

function formatarNumero(valor, decimais = 0) {
    if (valor === null || valor === undefined) return '-';
    return Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: decimais,
        maximumFractionDigits: decimais
    });
}

// ==========================================================================
// SALVAR CUSTO
// ==========================================================================
function handleEnterKey(event, input) {
    if (event.key === 'Enter') {
        event.preventDefault();
        salvarCusto(input);
        input.blur();
    }
}

function salvarCusto(input) {
    if (salvandoCusto) return;

    const codProduto = input.dataset.codProduto;
    const custoConsiderado = parseFloat(input.value);

    if (isNaN(custoConsiderado) || custoConsiderado < 0) {
        return;
    }

    salvandoCusto = true;
    input.classList.add('is-loading');

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/definicao/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            cod_produto: codProduto,
            custo_considerado: custoConsiderado
        })
    })
    .then(r => r.json())
    .then(data => {
        salvandoCusto = false;
        input.classList.remove('is-loading');

        if (data.sucesso) {
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 2000);

            // Atualizar dados locais
            const item = dadosDefinicao.find(d => d.cod_produto === codProduto);
            if (item) {
                item.custo_considerado = custoConsiderado;
            }
        } else {
            input.classList.add('is-invalid');
            setTimeout(() => input.classList.remove('is-invalid'), 2000);
            console.error('Erro ao salvar:', data.erro);
        }
    })
    .catch(err => {
        salvandoCusto = false;
        input.classList.remove('is-loading');
        input.classList.add('is-invalid');
        setTimeout(() => input.classList.remove('is-invalid'), 2000);
        console.error(err);
    });
}

// ==========================================================================
// IMPORT/EXPORT
// ==========================================================================
function exportarDefinicao() {
    const tipo = document.getElementById('filtro-tipo').value;
    window.location.href = `/custeio/api/definicao/exportar?tipo=${tipo}`;
}

function baixarModelo() {
    window.location.href = '/custeio/api/definicao/modelo';
}

function importarDefinicao(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/definicao/importar', {
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
