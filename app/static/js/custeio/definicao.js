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

    // Buscar composição BOM com TODOS os 4 custos
    fetch(`/custeio/api/definicao/bom/${codProduto}?criterio=${tipoValor}`)
        .then(r => r.json())
        .then(data => {
            loadingRow.remove();

            if (!data.sucesso || !data.componentes || data.componentes.length === 0) {
                const emptyRow = criarLinhaDetalheVazia(codProduto, tipoValor, 'Sem componentes BOM');
                rowPai.after(emptyRow);
                return;
            }

            // Linha de total primeiro (será inserida por último visualmente)
            const totalRow = criarLinhaTotalBOM(codProduto, tipoValor, data.totais, data.criterio_selecionado);
            rowPai.after(totalRow);

            // Criar linhas de componentes (em ordem reversa para inserir corretamente)
            const componentes = data.componentes.slice().reverse();
            for (const comp of componentes) {
                const compRow = criarLinhaComponenteBOM(codProduto, tipoValor, comp, data.criterio_selecionado);
                rowPai.after(compRow);
            }

            // Linha de cabeçalho dos custos
            const headerRow = criarLinhaCabecalhoBOM(codProduto, tipoValor, data.criterio_selecionado);
            rowPai.after(headerRow);
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

function criarLinhaCabecalhoBOM(codProduto, tipoValor, criterioSelecionado) {
    const row = document.createElement('tr');
    row.className = 'detail-row bom-header';
    row.dataset.parent = codProduto;
    row.dataset.tipo = tipoValor;

    const tipos = ['medio_mes', 'ultimo_custo', 'medio_estoque', 'custo_considerado'];

    row.innerHTML = `
        <td></td>
        <td class="small fw-bold text-muted">Componente</td>
        <td class="small fw-bold text-muted">Qtd</td>
        ${tipos.map(t => `
            <td class="text-center small fw-bold bom-custo-header ${t === criterioSelecionado ? 'custo-destacado' : ''}">
                ${getNomeCriterioAbrev(t)}
            </td>
        `).join('')}
    `;
    return row;
}

function criarLinhaComponenteBOM(codProduto, tipoValor, comp, criterioSelecionado) {
    const row = document.createElement('tr');
    row.className = 'detail-row bom-row bom-multi-custo';
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

    // Tipos de custo
    const tipos = ['medio_mes', 'ultimo_custo', 'medio_estoque', 'custo_considerado'];

    // Criar células de custo
    const celulasCusto = tipos.map(tipo => {
        const custo = comp.custos?.[tipo] || {};
        const unitario = custo.unitario;
        const total = custo.total;
        const eDestacado = tipo === criterioSelecionado;

        return `
            <td class="text-end small bom-custo-cell ${eDestacado ? 'custo-destacado' : ''}"
                onclick="abrirModalDetalhesCusto('${comp.cod_produto}', '${tipo}')"
                title="Clique para ver detalhes">
                <div class="custo-unitario">${formatarMoedaCompacto(unitario)}</div>
                <div class="custo-total text-muted">${formatarMoedaCompacto(total)}</div>
            </td>
        `;
    }).join('');

    row.innerHTML = `
        <td></td>
        <td class="ps-3 small">
            ${indent}${prefixo} <code>${comp.cod_produto}</code> ${tipoBadge}
            <div class="text-muted small">${comp.nome_produto || ''}</div>
        </td>
        <td class="text-end small">${formatarNumero(comp.qtd_utilizada, 4)}</td>
        ${celulasCusto}
    `;

    return row;
}

function criarLinhaTotalBOM(codProduto, tipoValor, totais, criterioSelecionado) {
    const row = document.createElement('tr');
    row.className = 'detail-row bom-total';
    row.dataset.parent = codProduto;
    row.dataset.tipo = tipoValor;

    const tipos = ['medio_mes', 'ultimo_custo', 'medio_estoque', 'custo_considerado'];

    const celulasTotais = tipos.map(tipo => {
        const total = totais?.[tipo];
        const eDestacado = tipo === criterioSelecionado;

        return `
            <td class="text-end small fw-bold bom-custo-cell ${eDestacado ? 'custo-destacado' : ''}">
                ${formatarMoeda(total)}
            </td>
        `;
    }).join('');

    row.innerHTML = `
        <td></td>
        <td class="text-end small fw-bold text-muted">TOTAL BOM:</td>
        <td></td>
        ${celulasTotais}
    `;
    return row;
}

function getNomeCriterioAbrev(tipoValor) {
    switch (tipoValor) {
        case 'medio_mes': return 'Méd.Mês';
        case 'ultimo_custo': return 'Últ.Custo';
        case 'medio_estoque': return 'Méd.Est.';
        case 'custo_considerado': return 'Consid.';
        default: return tipoValor;
    }
}

function formatarMoedaCompacto(valor) {
    if (valor === null || valor === undefined) return '-';
    return Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
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

function exportarCustosDetalhados(codProduto = null) {
    // Exporta custos detalhados com BOM recursivo
    // Se codProduto for passado, exporta apenas aquele produto
    // Senão, exporta todos ACABADOS/INTERMEDIARIOS
    let url = '/custeio/api/definicao/exportar-detalhado';
    if (codProduto) {
        url += `?cod_produto=${codProduto}`;
    }
    window.location.href = url;
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

// ==========================================================================
// MODAL DE DETALHES DO CUSTO
// ==========================================================================
let modalDetalhesCustoInstance = null;
let modalHistoricoAtivo = false;

async function abrirModalDetalhesCusto(codProduto, tipoCusto) {
    const modal = document.getElementById('modalDetalhesCusto');
    if (!modal) {
        console.error('Modal de detalhes não encontrado');
        return;
    }

    if (!modalDetalhesCustoInstance) {
        modalDetalhesCustoInstance = new bootstrap.Modal(modal);
    }

    const conteudo = document.getElementById('conteudo-modal-custo');
    const titulo = document.getElementById('titulo-modal-custo');

    // Loading
    titulo.innerHTML = `<i class="bi bi-search me-2"></i>Carregando...`;
    conteudo.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Buscando detalhes do custo...</p>
        </div>
    `;
    modalDetalhesCustoInstance.show();

    // Reset histórico
    modalHistoricoAtivo = false;

    try {
        const resp = await fetch(`/custeio/api/definicao/custo-detalhes/${codProduto}?tipo=${tipoCusto}`);
        const dados = await resp.json();

        if (!dados.sucesso) {
            conteudo.innerHTML = `<div class="alert alert-danger">${dados.erro || 'Erro ao carregar dados'}</div>`;
            return;
        }

        // Atualizar título
        titulo.innerHTML = `
            <i class="bi bi-search me-2"></i>
            ${getNomeCriterio(tipoCusto)} - ${dados.cod_produto}
        `;

        // Renderizar baseado no tipo
        if (tipoCusto === 'medio_mes' || tipoCusto === 'ultimo_custo') {
            conteudo.innerHTML = renderizarModalPedidos(dados, tipoCusto, codProduto);
        } else if (tipoCusto === 'medio_estoque') {
            conteudo.innerHTML = renderizarModalEstoque(dados, codProduto);
        } else if (tipoCusto === 'custo_considerado') {
            conteudo.innerHTML = renderizarModalConsiderado(dados);
        }

    } catch (err) {
        console.error(err);
        conteudo.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados: ${err.message}</div>`;
    }
}

async function toggleHistorico(codProduto, tipoCusto) {
    modalHistoricoAtivo = !modalHistoricoAtivo;
    const btn = document.getElementById('btn-historico');
    if (btn) {
        btn.innerHTML = modalHistoricoAtivo
            ? '<i class="bi bi-calendar-check me-1"></i>Ver Período'
            : '<i class="bi bi-clock-history me-1"></i>Últimos 90 dias';
    }

    const conteudo = document.getElementById('conteudo-modal-custo');
    conteudo.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <span class="ms-2">Atualizando...</span>
        </div>
    `;

    try {
        const resp = await fetch(`/custeio/api/definicao/custo-detalhes/${codProduto}?tipo=${tipoCusto}&historico=${modalHistoricoAtivo}`);
        const dados = await resp.json();

        if (tipoCusto === 'medio_mes' || tipoCusto === 'ultimo_custo') {
            conteudo.innerHTML = renderizarModalPedidos(dados, tipoCusto, codProduto);
        } else if (tipoCusto === 'medio_estoque') {
            conteudo.innerHTML = renderizarModalEstoque(dados, codProduto);
        }
    } catch (err) {
        conteudo.innerHTML = `<div class="alert alert-danger">Erro: ${err.message}</div>`;
    }
}

function renderizarModalPedidos(dados, tipoCusto, codProduto) {
    const { resumo, pedidos, periodo, nome_produto } = dados;

    const periodoLabel = periodo?.historico
        ? `${periodo.data_inicio} a ${periodo.data_fim}`
        : `${String(periodo?.mes || '').padStart(2, '0')}/${periodo?.ano || ''}`;

    let html = `
        <div class="mb-3">
            <h6 class="mb-1">${nome_produto || codProduto}</h6>
            <small class="text-muted">Período: ${periodoLabel}</small>
            <button class="btn btn-outline-secondary btn-sm ms-2" id="btn-historico"
                    onclick="toggleHistorico('${codProduto}', '${tipoCusto}')">
                <i class="bi bi-clock-history me-1"></i>${periodo?.historico ? 'Ver Período' : 'Últimos 90 dias'}
            </button>
        </div>

        <!-- Resumo -->
        <div class="card mb-3 card-resumo-custo">
            <div class="card-body py-2">
                <div class="row text-center">
                    <div class="col">
                        <div class="small text-muted">Pedidos</div>
                        <div class="fw-bold">${resumo?.qtd_pedidos || 0}</div>
                    </div>
                    <div class="col">
                        <div class="small text-muted">Qtd Comprada</div>
                        <div class="fw-bold">${formatarNumero(resumo?.qtd_comprada, 3)}</div>
                    </div>
                    <div class="col">
                        <div class="small text-muted">Valor Bruto</div>
                        <div class="fw-bold">${formatarMoeda(resumo?.valor_bruto)}</div>
                    </div>
                    <div class="col">
                        <div class="small text-muted">Impostos</div>
                        <div class="fw-bold text-danger">${formatarMoeda((resumo?.icms || 0) + (resumo?.pis || 0) + (resumo?.cofins || 0))}</div>
                    </div>
                    <div class="col">
                        <div class="small text-muted">Valor Líquido</div>
                        <div class="fw-bold text-success">${formatarMoeda(resumo?.valor_liquido)}</div>
                    </div>
                    <div class="col">
                        <div class="small text-muted">Custo Médio</div>
                        <div class="fw-bold text-primary fs-5">${formatarMoeda(resumo?.custo_medio)}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (pedidos && pedidos.length > 0) {
        html += `
            <div class="table-responsive">
                <table class="table table-sm table-hover tabela-pedidos-compra">
                    <thead>
                        <tr>
                            <th>Pedido</th>
                            <th>Fornecedor</th>
                            <th>Data</th>
                            <th>NF</th>
                            <th class="text-end">Qtd</th>
                            <th class="text-end">Preço Unit.</th>
                            <th class="text-end">Bruto</th>
                            <th class="text-end">ICMS</th>
                            <th class="text-end">PIS</th>
                            <th class="text-end">COFINS</th>
                            <th class="text-end">Líquido</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${pedidos.map(p => `
                            <tr>
                                <td><code>${p.num_pedido || '-'}</code></td>
                                <td class="text-truncate" style="max-width: 150px;" title="${p.fornecedor}">${p.fornecedor || '-'}</td>
                                <td>${p.data || '-'}</td>
                                <td>${p.numero_nf || '-'}</td>
                                <td class="text-end">${formatarNumero(p.qtd_recebida, 3)}</td>
                                <td class="text-end">${formatarMoeda(p.preco_unitario)}</td>
                                <td class="text-end">${formatarMoeda(p.valor_bruto)}</td>
                                <td class="text-end text-danger">${formatarMoeda(p.icms)}</td>
                                <td class="text-end text-danger">${formatarMoeda(p.pis)}</td>
                                <td class="text-end text-danger">${formatarMoeda(p.cofins)}</td>
                                <td class="text-end text-success fw-bold">${formatarMoeda(p.valor_liquido)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } else {
        html += `<div class="alert alert-info">Nenhum pedido de compra encontrado no período.</div>`;
    }

    return html;
}

function renderizarModalEstoque(dados, codProduto) {
    const { estoque_inicial, compras, estoque_final, formula, pedidos, periodo, nome_produto } = dados;

    let html = `
        <div class="mb-3">
            <h6 class="mb-1">${nome_produto || codProduto}</h6>
            <small class="text-muted">Período: ${String(periodo?.mes || '').padStart(2, '0')}/${periodo?.ano || ''}</small>
            <button class="btn btn-outline-secondary btn-sm ms-2" id="btn-historico"
                    onclick="toggleHistorico('${codProduto}', 'medio_estoque')">
                <i class="bi bi-clock-history me-1"></i>${periodo?.historico ? 'Ver Período' : 'Últimos 90 dias'}
            </button>
        </div>

        <!-- Cards de Estoque -->
        <div class="row g-3 mb-3">
            <div class="col-md-4">
                <div class="card-estoque h-100">
                    <div class="card-header-themed header-secondary">
                        <small>Estoque Inicial</small>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Quantidade:</span>
                            <span class="fw-bold">${formatarNumero(estoque_inicial?.qtd, 3)}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Valor Total:</span>
                            <span class="fw-bold">${formatarMoeda(estoque_inicial?.valor)}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Custo Unit.:</span>
                            <span class="fw-bold text-primary">${formatarMoeda(estoque_inicial?.custo_unitario)}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card-estoque h-100">
                    <div class="card-header-themed header-info">
                        <small>Compras no Período (${compras?.qtd_pedidos || 0} pedidos)</small>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Quantidade:</span>
                            <span class="fw-bold">${formatarNumero(compras?.qtd, 3)}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Valor Líquido:</span>
                            <span class="fw-bold text-success">${formatarMoeda(compras?.valor_liquido)}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card-estoque h-100">
                    <div class="card-header-themed header-success">
                        <small>Estoque Final</small>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Quantidade:</span>
                            <span class="fw-bold">${formatarNumero(estoque_final?.qtd, 3)}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Valor Total:</span>
                            <span class="fw-bold">${formatarMoeda(estoque_final?.valor)}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Custo Médio:</span>
                            <span class="fw-bold text-success fs-5">${formatarMoeda(estoque_final?.custo_medio)}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Fórmula -->
        <div class="formula-custo mb-3">
            <i class="bi bi-calculator me-2"></i>
            <strong>Fórmula:</strong> ${formula || '-'}
        </div>
    `;

    if (pedidos && pedidos.length > 0) {
        html += `
            <h6 class="mb-2">Pedidos de Compra no Período</h6>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead>
                        <tr>
                            <th>Pedido</th>
                            <th>Fornecedor</th>
                            <th>Data</th>
                            <th class="text-end">Qtd</th>
                            <th class="text-end">Valor Líquido</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${pedidos.map(p => `
                            <tr>
                                <td><code>${p.num_pedido || '-'}</code></td>
                                <td>${p.fornecedor || '-'}</td>
                                <td>${p.data || '-'}</td>
                                <td class="text-end">${formatarNumero(p.qtd_recebida, 3)}</td>
                                <td class="text-end text-success">${formatarMoeda(p.valor_liquido)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    return html;
}

function renderizarModalConsiderado(dados) {
    const { atual, historico, nome_produto, cod_produto } = dados;

    let html = `
        <div class="mb-3">
            <h6 class="mb-1">${nome_produto || cod_produto}</h6>
        </div>
    `;

    if (atual) {
        html += `
            <div class="card-estoque mb-3">
                <div class="card-header-themed header-success">
                    <small>Custo Atual</small>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4 text-center">
                            <div class="text-muted small">Valor</div>
                            <div class="fs-3 fw-bold text-success">${formatarMoeda(atual.valor)}</div>
                        </div>
                        <div class="col-md-4 text-center">
                            <div class="text-muted small">Tipo Base</div>
                            <div class="fw-bold">${atual.tipo_base || '-'}</div>
                        </div>
                        <div class="col-md-4 text-center">
                            <div class="text-muted small">Atualizado</div>
                            <div class="small">${atual.atualizado_em || '-'}</div>
                            <div class="small text-muted">por ${atual.atualizado_por || 'Sistema'}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    if (historico && historico.length > 0) {
        html += `
            <h6 class="mb-2">Histórico de Versões</h6>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead>
                        <tr>
                            <th>Versão</th>
                            <th class="text-end">Custo</th>
                            <th>Tipo</th>
                            <th>Vigência Início</th>
                            <th>Vigência Fim</th>
                            <th>Motivo</th>
                            <th>Por</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${historico.map(v => `
                            <tr class="${v.atual ? 'table-row-success' : ''}">
                                <td>${v.versao}${v.atual ? ' <span class="badge bg-success">Atual</span>' : ''}</td>
                                <td class="text-end fw-bold">${formatarMoeda(v.custo_considerado)}</td>
                                <td><span class="badge bg-secondary">${v.tipo_selecionado || '-'}</span></td>
                                <td class="small">${v.vigencia_inicio || '-'}</td>
                                <td class="small">${v.vigencia_fim || '-'}</td>
                                <td class="small text-truncate" style="max-width: 150px;" title="${v.motivo || ''}">${v.motivo || '-'}</td>
                                <td class="small">${v.atualizado_por || '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    return html;
}
