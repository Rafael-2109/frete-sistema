/**
 * PROGRAMAÇÃO POR LINHA - AGRUPAMENTOS (Por Linha, Por Dia, Por Produto)
 * Replica estilo do modalSeparacoesProduto
 */

// ============================================================
// ESTADO GLOBAL
// ============================================================

let currentAgrupamento = 'linha'; // 'linha', 'dia', 'produto'
let dadosFiltrados = []; // Dados após aplicar filtros
let linhasDisponiveis = [];
let produtosDisponiveis = [];

// ============================================================
// INICIALIZAÇÃO
// ============================================================

$(document).ready(function() {
    // Listener do radio de agrupamento
    $('input[name="agrupamento"]').on('change', function() {
        currentAgrupamento = $(this).val();
        atualizarTituloAgrupamento();
        renderizarAgrupamento();
    });

    // Listeners dos filtros
    $('#filtro-linha').on('change', aplicarFiltros);
    $('#filtro-produto').on('change', aplicarFiltros);
    $('#filtro-data').on('change', aplicarFiltros);
    $('#btn-limpar-filtros').on('click', limparFiltros);

    // Botões expandir/colapsar
    $('#btn-expandir-todos').on('click', () => {
        $('#programacao-container .accordion-collapse').addClass('show');
        $('#programacao-container .accordion-button').removeClass('collapsed');
    });

    $('#btn-colapsar-todos').on('click', () => {
        $('#programacao-container .accordion-collapse').removeClass('show');
        $('#programacao-container .accordion-button').addClass('collapsed');
    });
});

// ============================================================
// FUNÇÕES PRINCIPAIS
// ============================================================

/**
 * Atualiza título do agrupamento
 */
function atualizarTituloAgrupamento() {
    const titulos = {
        'linha': 'Programação por Linha de Produção',
        'dia': 'Programação por Dia',
        'produto': 'Programação por Produto'
    };
    $('#titulo-agrupamento').text(titulos[currentAgrupamento]);
}

/**
 * Processa dados e renderiza agrupamento atual
 */
function renderizarAgrupamento() {
    if (!programacaoState.linhas || programacaoState.linhas.length === 0) {
        $('#programacao-container').html(`
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Nenhuma programação encontrada para o período selecionado.
            </div>
        `);
        return;
    }

    // Aplicar filtros primeiro
    aplicarFiltros();
}

/**
 * Aplica filtros nos dados
 */
function aplicarFiltros() {
    const filtroLinha = $('#filtro-linha').val();
    const filtroProduto = $('#filtro-produto').val();
    const filtroData = $('#filtro-data').val();

    console.log('[FILTROS] Linha:', filtroLinha, '| Produto:', filtroProduto, '| Data:', filtroData);

    // Começar com todos os dados
    dadosFiltrados = JSON.parse(JSON.stringify(programacaoState.linhas)); // Deep copy

    // Aplicar filtros
    if (filtroLinha) {
        dadosFiltrados = dadosFiltrados.filter(l => l.linha_producao === filtroLinha);
    }

    if (filtroProduto) {
        dadosFiltrados = dadosFiltrados.map(linha => {
            const novaLinha = {...linha};
            novaLinha.programacoes = {};
            Object.keys(linha.programacoes).forEach(dia => {
                const progsFiltradas = linha.programacoes[dia].filter(p => p.cod_produto === filtroProduto);
                if (progsFiltradas.length > 0) {
                    novaLinha.programacoes[dia] = progsFiltradas;
                }
            });
            return novaLinha;
        }).filter(l => Object.keys(l.programacoes).length > 0);
    }

    if (filtroData) {
        dadosFiltrados = dadosFiltrados.map(linha => {
            const novaLinha = {...linha};
            novaLinha.programacoes = {};
            if (linha.programacoes[filtroData]) {
                novaLinha.programacoes[filtroData] = linha.programacoes[filtroData];
            }
            return novaLinha;
        }).filter(l => Object.keys(l.programacoes).length > 0);
    }

    // Renderizar agrupamento
    switch(currentAgrupamento) {
        case 'linha':
            renderizarPorLinha(dadosFiltrados);
            break;
        case 'dia':
            renderizarPorDia(dadosFiltrados);
            break;
        case 'produto':
            renderizarPorProduto(dadosFiltrados);
            break;
    }
}

/**
 * Limpa todos os filtros
 */
function limparFiltros() {
    $('#filtro-linha').val('');
    $('#filtro-produto').val('');
    $('#filtro-data').val('');
    aplicarFiltros();
}

/**
 * Popula dropdowns de filtros
 */
function popularFiltros(linhas) {
    // Extrair linhas únicas
    linhasDisponiveis = [...new Set(linhas.map(l => l.linha_producao))].sort();

    const $selectLinha = $('#filtro-linha');
    $selectLinha.html('<option value="">Todas as linhas</option>');
    linhasDisponiveis.forEach(linha => {
        $selectLinha.append(`<option value="${linha}">${linha}</option>`);
    });

    // Extrair produtos únicos
    const produtos = new Set();
    linhas.forEach(linha => {
        Object.values(linha.programacoes).forEach(progs => {
            progs.forEach(p => produtos.add(`${p.cod_produto}|${p.nome_produto}`));
        });
    });

    produtosDisponiveis = [...produtos].sort();

    const $selectProduto = $('#filtro-produto');
    $selectProduto.html('<option value="">Todos os produtos</option>');
    produtosDisponiveis.forEach(item => {
        const [cod, nome] = item.split('|');
        $selectProduto.append(`<option value="${cod}">${cod} - ${nome}</option>`);
    });
}

// ============================================================
// RENDERIZAÇÃO POR LINHA (IGUAL AO MODAL)
// ============================================================

function renderizarPorLinha(linhas) {
    console.log('[POR LINHA] Renderizando', linhas.length, 'linhas');

    if (!linhas || linhas.length === 0) {
        $('#programacao-container').html(`
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Nenhuma programação encontrada com os filtros aplicados.
            </div>
        `);
        $('#total-programacoes').text('0 programações');
        $('#total-grupos').text('0 linhas');
        return;
    }

    let html = '<div class="accordion" id="accordion-por-linha">';
    let totalProgramacoes = 0;
    let index = 0;

    linhas.forEach(linha => {
        const programacoes = linha.programacoes;
        const numDias = Object.keys(programacoes).length;

        // Contar programações
        let qtdTotal = 0;
        Object.values(programacoes).forEach(progs => {
            qtdTotal += progs.reduce((sum, p) => sum + (parseFloat(p.qtd_programada) || 0), 0);
            totalProgramacoes += progs.length;
        });

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${index === 0 ? '' : 'collapsed'}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#collapse-linha-${index}">
                        <div class="d-flex justify-content-between w-100 me-3">
                            <div><strong>${linha.linha_producao}</strong></div>
                            <div>
                                <span class="badge bg-primary me-2">Qtd total: ${formatarNumero(qtdTotal, 0)}</span>
                                <span class="badge bg-secondary">${numDias} dias</span>
                            </div>
                        </div>
                    </button>
                </h2>
                <div id="collapse-linha-${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     data-bs-parent="#accordion-por-linha">
                    <div class="accordion-body p-0">
                        <table class="table table-sm table-bordered table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th style="width: 100px;">Data</th>
                                    <th>Programações</th>
                                </tr>
                            </thead>
                            <tbody>`;

        // Ordenar datas
        const datasOrdenadas = Object.keys(programacoes).sort();

        datasOrdenadas.forEach(data => {
            const progs = programacoes[data];
            const dataFormatada = formatarData(data);

            html += `<tr><td class="fw-bold align-top">${dataFormatada}</td><td>`;

            // Empilhar programações verticalmente (igual ao modal)
            progs.forEach(prog => {
                html += renderizarItemProgramacao(prog);
            });

            html += '</td></tr>';
        });

        html += '</tbody></table></div></div></div>';
        index++;
    });

    html += '</div>';

    $('#programacao-container').html(html);
    $('#total-programacoes').text(`${totalProgramacoes} programações`);
    $('#total-grupos').text(`${linhas.length} linhas`);

    ativarTooltips();
}

// ============================================================
// RENDERIZAÇÃO POR DIA
// ============================================================

function renderizarPorDia(linhas) {
    console.log('[POR DIA] Renderizando');

    // Agrupar por dia
    const porDia = {};
    linhas.forEach(linha => {
        Object.keys(linha.programacoes).forEach(dia => {
            if (!porDia[dia]) porDia[dia] = [];
            linha.programacoes[dia].forEach(prog => {
                porDia[dia].push({...prog, linha_producao: linha.linha_producao});
            });
        });
    });

    const dias = Object.keys(porDia).sort();

    if (dias.length === 0) {
        $('#programacao-container').html(`
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Nenhuma programação encontrada com os filtros aplicados.
            </div>
        `);
        $('#total-programacoes').text('0 programações');
        $('#total-grupos').text('0 dias');
        return;
    }

    let html = '<div class="accordion" id="accordion-por-dia">';
    let totalProgramacoes = 0;
    let index = 0;

    dias.forEach(dia => {
        const progs = porDia[dia];
        const dataFormatada = formatarData(dia);
        const qtdTotal = progs.reduce((sum, p) => sum + (parseFloat(p.qtd_programada) || 0), 0);
        totalProgramacoes += progs.length;

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${index === 0 ? '' : 'collapsed'}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#collapse-dia-${index}">
                        <div class="d-flex justify-content-between w-100 me-3">
                            <div><strong>${dataFormatada}</strong></div>
                            <div>
                                <span class="badge bg-primary me-2">Qtd total: ${formatarNumero(qtdTotal, 0)}</span>
                                <span class="badge bg-secondary">${progs.length} programações</span>
                            </div>
                        </div>
                    </button>
                </h2>
                <div id="collapse-dia-${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     data-bs-parent="#accordion-por-dia">
                    <div class="accordion-body p-2">`;

        progs.forEach(prog => {
            html += renderizarItemProgramacao(prog, true); // true = mostrar linha
        });

        html += '</div></div></div>';
        index++;
    });

    html += '</div>';

    $('#programacao-container').html(html);
    $('#total-programacoes').text(`${totalProgramacoes} programações`);
    $('#total-grupos').text(`${dias.length} dias`);

    ativarTooltips();
}

// ============================================================
// RENDERIZAÇÃO POR PRODUTO
// ============================================================

function renderizarPorProduto(linhas) {
    console.log('[POR PRODUTO] Renderizando');

    // Agrupar por produto
    const porProduto = {};
    linhas.forEach(linha => {
        Object.keys(linha.programacoes).forEach(dia => {
            linha.programacoes[dia].forEach(prog => {
                const key = prog.cod_produto;
                if (!porProduto[key]) {
                    porProduto[key] = {
                        cod_produto: prog.cod_produto,
                        nome_produto: prog.nome_produto,
                        programacoes: []
                    };
                }
                porProduto[key].programacoes.push({
                    ...prog,
                    linha_producao: linha.linha_producao,
                    data_programacao: dia
                });
            });
        });
    });

    const produtos = Object.values(porProduto).sort((a, b) =>
        a.cod_produto.localeCompare(b.cod_produto)
    );

    if (produtos.length === 0) {
        $('#programacao-container').html(`
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Nenhuma programação encontrada com os filtros aplicados.
            </div>
        `);
        $('#total-programacoes').text('0 programações');
        $('#total-grupos').text('0 produtos');
        return;
    }

    let html = '<div class="accordion" id="accordion-por-produto">';
    let totalProgramacoes = 0;
    let index = 0;

    produtos.forEach(produto => {
        const progs = produto.programacoes;
        const qtdTotal = progs.reduce((sum, p) => sum + (parseFloat(p.qtd_programada) || 0), 0);
        totalProgramacoes += progs.length;

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${index === 0 ? '' : 'collapsed'}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#collapse-produto-${index}">
                        <div class="d-flex justify-content-between w-100 me-3">
                            <div>
                                <strong class="clickable-produto" data-cod="${produto.cod_produto}"
                                        style="cursor:pointer; color: #0d6efd; text-decoration: underline;"
                                        title="Clique para ver separações e estoque">
                                    ${produto.cod_produto}
                                </strong> - ${produto.nome_produto}
                            </div>
                            <div>
                                <span class="badge bg-primary me-2">Qtd total: ${formatarNumero(qtdTotal, 0)}</span>
                                <span class="badge bg-secondary">${progs.length} programações</span>
                            </div>
                        </div>
                    </button>
                </h2>
                <div id="collapse-produto-${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     data-bs-parent="#accordion-por-produto">
                    <div class="accordion-body p-2">`;

        // ✅ Renderizar programações por produto (SEM repetir produto, SEM badges)
        progs.forEach(prog => {
            html += renderizarItemPorProduto(prog);
        });

        html += '</div></div></div>';
        index++;
    });

    html += '</div>';

    $('#programacao-container').html(html);
    $('#total-programacoes').text(`${totalProgramacoes} programações`);
    $('#total-grupos').text(`${produtos.length} produtos`);

    ativarTooltips();
}

// ============================================================
// RENDERIZAÇÃO DE ITEM INDIVIDUAL (IGUAL AO MODAL)
// ============================================================

function renderizarItemProgramacao(prog, mostrarLinha = false, mostrarData = false) {
    const progId = prog.id || 0;
    const comHistorico = programacaoState.comHistorico;
    const isExtraProducao = prog.is_extra_producao || false;

    // Classes CSS para produção extra (destaque visual)
    const extraClass = isExtraProducao ? 'border-warning bg-light' : '';
    const extraBadge = isExtraProducao ? ' <span class="badge bg-warning text-dark ms-2" title="Produção não programada">⚠️ Extra</span>' : '';

    let html = `
        <div class="p-2 mb-1 border rounded programacao-item ${extraClass}" data-prog-id="${progId}">
            <div class="d-flex justify-content-between align-items-center gap-2">
                <div class="flex-grow-1">
                    <strong class="clickable-produto" data-cod="${prog.cod_produto}" style="cursor:pointer; color: #0d6efd;">
                        ${prog.cod_produto}
                    </strong> - ${prog.nome_produto || ''}${extraBadge}`;

    if (mostrarLinha) {
        html += ` <span class="badge bg-info ms-2">${prog.linha_producao}</span>`;
    }

    if (mostrarData) {
        html += ` <span class="badge bg-secondary ms-1">${formatarData(prog.data_programacao)}</span>`;
    }

    html += `
                </div>
                <div class="d-flex align-items-center gap-2">`;

    // Se com histórico, mostrar tabela Programado/Produzido/Diferença (somente leitura)
    if (comHistorico) {
        const qtdProgramada = parseFloat(prog.qtd_programada) || 0;
        const qtdProduzida = parseFloat(prog.qtd_produzida) || 0;
        const diferenca = qtdProduzida - qtdProgramada;
        const percentual = qtdProgramada > 0 ? ((qtdProduzida / qtdProgramada) * 100) : 0;

        // Cores baseadas no percentual
        let corProducao = 'text-muted';
        if (qtdProduzida > 0) {
            if (percentual >= 95) corProducao = 'text-success';
            else if (percentual >= 80) corProducao = 'text-warning';
            else corProducao = 'text-danger';
        }

        html += `
                    <div class="d-flex align-items-center gap-2" style="font-size: 0.85rem;">
                        <div class="text-center" style="min-width: 80px;">
                            <div class="text-muted small">Programado</div>
                            <strong>${formatarNumero(qtdProgramada, 0)}</strong>
                        </div>
                        <div class="text-center ${corProducao}" style="min-width: 80px;">
                            <div class="text-muted small">Produzido</div>
                            <strong>${formatarNumero(qtdProduzida, 0)}</strong>
                        </div>
                        <div class="text-center" style="min-width: 90px;">
                            <div class="text-muted small">Diferença</div>
                            <strong class="${diferenca >= 0 ? 'text-success' : 'text-danger'}">
                                ${diferenca >= 0 ? '+' : ''}${formatarNumero(diferenca, 0)}
                            </strong>
                            <span class="badge ${percentual >= 95 ? 'bg-success' : percentual >= 80 ? 'bg-warning' : 'bg-danger'} ms-1" style="font-size: 0.7rem;">
                                ${formatarNumero(percentual, 1)}%
                            </span>
                        </div>
                    </div>`;
    } else {
        // Modo edição (sem histórico) - inputs inline
        const obsValue = prog.observacao_pcp || '';
        const opValue = prog.ordem_producao || '';

        html += `
                    <!-- Input Ordem Produção (editável inline) -->
                    <input type="text" class="form-control form-control-sm input-edit-op"
                           value="${opValue}"
                           onblur="salvarEdicaoCampo(${progId}, 'ordem_producao', this.value)"
                           placeholder="OP"
                           style="width: 80px;" title="Ordem de Produção">

                    <!-- Input Observação PCP (editável inline) -->
                    <input type="text" class="form-control form-control-sm input-edit-obs"
                           value="${obsValue}"
                           onblur="salvarEdicaoCampo(${progId}, 'observacao_pcp', this.value)"
                           placeholder="Obs..."
                           style="width: 120px;" title="Observação PCP">

                    <!-- Input de Data (editável) -->
                    <input type="date" class="form-control form-control-sm input-edit-data"
                           value="${prog.data_programacao}"
                           onchange="salvarEdicaoProgramacao(${progId}, this.value, null)"
                           style="width: 140px;" title="Alterar data">

                    <!-- Input de Quantidade (editável) -->
                    <input type="number" class="form-control form-control-sm input-edit-qtd text-end"
                           value="${prog.qtd_programada}"
                           onchange="salvarEdicaoProgramacao(${progId}, null, this.value)"
                           step="0.001" min="0"
                           style="width: 100px;" title="Alterar quantidade">

                    <!-- Botão Excluir -->
                    <button class="btn btn-sm btn-outline-danger"
                            onclick="excluirProgramacao(${progId})"
                            title="Excluir programação">
                        <i class="fas fa-trash"></i>
                    </button>`;
    }

    html += `
                </div>
            </div>
        </div>`;

    return html;
}

/**
 * Renderiza item para agrupamento POR PRODUTO
 * - NÃO repete o código/nome do produto
 * - Mostra: Data - Linha (sem badges)
 * - Mantém inputs de edição e botão excluir
 */
function renderizarItemPorProduto(prog) {
    const progId = prog.id || 0;
    const comHistorico = programacaoState.comHistorico;
    const isExtraProducao = prog.is_extra_producao || false;

    // Destaque visual para produção extra
    const extraClass = isExtraProducao ? 'border-warning bg-light' : '';
    const extraBadge = isExtraProducao ? ' <span class="badge bg-warning text-dark ms-2" title="Produção não programada">⚠️ Extra</span>' : '';

    let html = `
        <div class="p-2 mb-1 border rounded programacao-item ${extraClass}" data-prog-id="${progId}">
            <div class="d-flex justify-content-between align-items-center gap-2">
                <div class="flex-grow-1">
                    <strong>${formatarData(prog.data_programacao)}</strong> - ${prog.linha_producao}${extraBadge}
                </div>
                <div class="d-flex align-items-center gap-2">`;

    // Se com histórico, mostrar Programado/Produzido/Diferença (somente leitura)
    if (comHistorico) {
        const qtdProgramada = parseFloat(prog.qtd_programada) || 0;
        const qtdProduzida = parseFloat(prog.qtd_produzida) || 0;
        const diferenca = qtdProduzida - qtdProgramada;
        const percentual = qtdProgramada > 0 ? ((qtdProduzida / qtdProgramada) * 100) : 0;

        let corProducao = 'text-muted';
        if (qtdProduzida > 0) {
            if (percentual >= 95) corProducao = 'text-success';
            else if (percentual >= 80) corProducao = 'text-warning';
            else corProducao = 'text-danger';
        }

        html += `
                    <div class="d-flex align-items-center gap-2" style="font-size: 0.85rem;">
                        <div class="text-center" style="min-width: 80px;">
                            <div class="text-muted small">Programado</div>
                            <strong>${formatarNumero(qtdProgramada, 0)}</strong>
                        </div>
                        <div class="text-center ${corProducao}" style="min-width: 80px;">
                            <div class="text-muted small">Produzido</div>
                            <strong>${formatarNumero(qtdProduzida, 0)}</strong>
                        </div>
                        <div class="text-center" style="min-width: 90px;">
                            <div class="text-muted small">Diferença</div>
                            <strong class="${diferenca >= 0 ? 'text-success' : 'text-danger'}">
                                ${diferenca >= 0 ? '+' : ''}${formatarNumero(diferenca, 0)}
                            </strong>
                            <span class="badge ${percentual >= 95 ? 'bg-success' : percentual >= 80 ? 'bg-warning' : 'bg-danger'} ms-1" style="font-size: 0.7rem;">
                                ${formatarNumero(percentual, 1)}%
                            </span>
                        </div>
                    </div>`;
    } else {
        // Modo edição (sem histórico) - inputs inline
        const obsValue = prog.observacao_pcp || '';
        const opValue = prog.ordem_producao || '';

        html += `
                    <!-- Input Ordem Produção (editável inline) -->
                    <input type="text" class="form-control form-control-sm input-edit-op"
                           value="${opValue}"
                           onblur="salvarEdicaoCampo(${progId}, 'ordem_producao', this.value)"
                           placeholder="OP"
                           style="width: 80px;" title="Ordem de Produção">

                    <!-- Input Observação PCP (editável inline) -->
                    <input type="text" class="form-control form-control-sm input-edit-obs"
                           value="${obsValue}"
                           onblur="salvarEdicaoCampo(${progId}, 'observacao_pcp', this.value)"
                           placeholder="Obs..."
                           style="width: 120px;" title="Observação PCP">

                    <!-- Input de Data (editável) -->
                    <input type="date" class="form-control form-control-sm input-edit-data"
                           value="${prog.data_programacao}"
                           onchange="salvarEdicaoProgramacao(${progId}, this.value, null)"
                           style="width: 140px;" title="Alterar data">

                    <!-- Input de Quantidade (editável) -->
                    <input type="number" class="form-control form-control-sm input-edit-qtd text-end"
                           value="${prog.qtd_programada}"
                           onchange="salvarEdicaoProgramacao(${progId}, null, this.value)"
                           step="0.001" min="0"
                           style="width: 100px;" title="Alterar quantidade">

                    <!-- Botão Excluir -->
                    <button class="btn btn-sm btn-outline-danger"
                            onclick="excluirProgramacao(${progId})"
                            title="Excluir programação">
                        <i class="fas fa-trash"></i>
                    </button>`;
    }

    html += `
                </div>
            </div>
        </div>`;

    return html;
}

// ============================================================
// FUNÇÕES DE EDIÇÃO E EXCLUSÃO
// ============================================================

/**
 * Salva edição de campo individual (observacao_pcp, ordem_producao)
 */
function salvarEdicaoCampo(id, campo, valor) {
    if (!id || id === 0) {
        console.warn('[EDITAR CAMPO] ID inválido:', id);
        return;
    }

    console.log('[EDITAR CAMPO] ID:', id, '| Campo:', campo, '| Valor:', valor);

    const dados = {};
    dados[campo] = valor;

    fetch(`/manufatura/recursos/api/programacao/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    })
    .then(response => response.json())
    .then(data => {
        if (!data.sucesso) {
            showToast('Erro ao atualizar: ' + (data.erro || 'Erro desconhecido'), 'error');
        }
        // Sucesso: silencioso para não interromper edição
    })
    .catch(error => {
        console.error('[EDITAR CAMPO] Erro:', error);
        showToast('Erro ao salvar alteração', 'error');
    });
}

function salvarEdicaoProgramacao(id, novaData, novaQtd) {
    console.log('[EDITAR] ID:', id, '| Data:', novaData, '| Qtd:', novaQtd);

    const dados = {};
    if (novaData) dados.data_programacao = novaData;
    if (novaQtd) dados.qtd_programada = parseFloat(novaQtd);

    fetch(`/manufatura/recursos/api/programacao/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            showToast('Programação atualizada com sucesso!', 'success');
            carregarProgramacaoLinhas(); // Recarregar dados
        } else {
            showToast('Erro ao atualizar: ' + (data.erro || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('[EDITAR] Erro:', error);
        showToast('Erro ao salvar alteração', 'error');
    });
}

function excluirProgramacao(id) {
    if (!confirm('Deseja realmente excluir esta programação?')) {
        return;
    }

    console.log('[EXCLUIR] ID:', id);

    fetch(`/manufatura/recursos/api/programacao/${id}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            showToast('Programação excluída com sucesso!', 'success');
            carregarProgramacaoLinhas(); // Recarregar dados
        } else {
            showToast('Erro ao excluir: ' + (data.erro || 'Erro desconhecido'), 'error');
        }
    })
    .catch(error => {
        console.error('[EXCLUIR] Erro:', error);
        showToast('Erro ao excluir programação', 'error');
    });
}

// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

function formatarNumero(num, decimais = 0) {
    if (!num) return '0';
    return parseFloat(num).toLocaleString('pt-BR', {
        minimumFractionDigits: decimais,
        maximumFractionDigits: decimais
    });
}

function formatarData(dataISO) {
    if (!dataISO) return '-';
    const [ano, mes, dia] = dataISO.split('-');
    return `${dia}/${mes}/${ano}`;
}

function ativarTooltips() {
    setTimeout(() => {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
    }, 100);
}

function showToast(message, type = 'info') {
    // Implementação simples de toast
    alert(message);
}

// ============================================================
// EVENTOS DE CLIQUE NO PRODUTO
// ============================================================

$(document).on('click', '.clickable-produto', function(e) {
    e.stopPropagation(); // ✅ Prevenir que abra/feche o accordion
    e.preventDefault();

    const codProduto = $(this).data('cod');
    console.log('[CLICK] Produto:', codProduto);

    // Usar data atual como referência
    const hoje = new Date().toISOString().split('T')[0];

    // Abrir modal
    if (typeof abrirModalSeparacoesProduto === 'function') {
        abrirModalSeparacoesProduto(codProduto, hoje);
    } else {
        alert('Função abrirModalSeparacoesProduto não encontrada');
    }
});

console.log('[AGRUPAMENTOS] Script carregado');
