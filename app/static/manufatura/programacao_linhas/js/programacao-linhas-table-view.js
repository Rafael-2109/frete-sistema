/**
 * PROGRAMAÇÃO POR LINHA - VISUALIZAÇÃO EM TABELA
 * Extensão para adicionar visualização em tabela (estilo modalSeparacoes)
 */

// ============================================================
// CONTROLE DE VISUALIZAÇÃO
// ============================================================

let currentView = 'accordion'; // 'accordion' ou 'table'

// Inicializar evento do toggle
$(document).ready(function() {
    // Listener do toggle de visualização
    $('input[name="visualizacao"]').on('change', function() {
        currentView = $(this).val();
        alternarVisualizacao(currentView);
    });

    // Mostrar/ocultar botões de expandir/colapsar conforme visualização
    alternarBotoesExpandir();
});

/**
 * Alterna entre visualização Accordion e Tabela
 */
function alternarVisualizacao(tipo) {
    console.log('[VIEW] Alternando para:', tipo);

    if (tipo === 'accordion') {
        // Mostrar accordion, ocultar tabela
        $('#accordion-linhas').removeClass('d-none');
        $('#table-view').addClass('d-none');
        $('#btn-expandir-todos, #btn-colapsar-todos').show();
    } else {
        // Mostrar tabela, ocultar accordion
        $('#accordion-linhas').addClass('d-none');
        $('#table-view').removeClass('d-none');
        $('#btn-expandir-todos, #btn-colapsar-todos').hide();

        // Renderizar visualização em tabela
        renderizarVisualizacaoTabela(programacaoState.linhas);
    }
}

function alternarBotoesExpandir() {
    const view = $('input[name="visualizacao"]:checked').val();
    if (view === 'accordion') {
        $('#btn-expandir-todos, #btn-colapsar-todos').show();
    } else {
        $('#btn-expandir-todos, #btn-colapsar-todos').hide();
    }
}

// ============================================================
// RENDERIZAÇÃO EM FORMATO TABELA
// ============================================================

function renderizarVisualizacaoTabela(linhas) {
    console.log('[TABLE VIEW] Renderizando', linhas.length, 'linhas');
    console.log('[TABLE VIEW] Estrutura da primeira linha:', linhas[0]);

    if (!linhas || linhas.length === 0) {
        $('#table-view').html(`
            <div class="alert alert-info m-3">
                <i class="fas fa-info-circle me-2"></i>
                Nenhuma programação encontrada para o período selecionado.
            </div>
        `);
        return;
    }

    // ✅ Agrupar produtos de todas as linhas
    // A estrutura é: linhas[].programacoes = {dia: [programacoes]}
    const todosProdutos = [];

    linhas.forEach(linha => {
        console.log('[TABLE VIEW] Processando linha:', linha.linha_producao);

        // Verificar se programacoes existe e é objeto
        if (linha.programacoes && typeof linha.programacoes === 'object') {
            // Iterar sobre cada dia
            Object.keys(linha.programacoes).forEach(dia => {
                const programacoesDia = linha.programacoes[dia];

                if (Array.isArray(programacoesDia) && programacoesDia.length > 0) {
                    console.log(`[TABLE VIEW] Dia ${dia}: ${programacoesDia.length} programações`);

                    programacoesDia.forEach(prog => {
                        todosProdutos.push({
                            linha_producao: linha.linha_producao,
                            cod_produto: prog.cod_produto,
                            nome_produto: prog.nome_produto,
                            quantidade: prog.qtd_programada,
                            data_prevista: dia,
                            id: prog.id || `${linha.linha_producao}-${prog.cod_produto}-${dia}` // Gerar ID se não existir
                        });
                    });
                }
            });
        }
    });

    console.log('[TABLE VIEW] Total de produtos extraídos:', todosProdutos.length);

    if (todosProdutos.length === 0) {
        $('#table-view').html(`
            <div class="alert alert-warning m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Nenhum produto programado para este período.
            </div>
        `);
        return;
    }

    // Montar HTML da tabela
    let html = '<div class="table-responsive p-3">';
    html += '<table class="table table-sm table-bordered table-hover">';
    html += '<thead class="table-light"><tr>';
    html += '<th>Linha Produção</th>';
    html += '<th>Código</th>';
    html += '<th>Produto</th>';
    html += '<th class="text-end">Quantidade</th>';
    html += '<th class="text-center">Data Prevista</th>';
    html += '<th class="text-center">Ações</th>';
    html += '</tr></thead><tbody>';

    todosProdutos.forEach(produto => {
        html += '<tr>';
        html += `<td><span class="badge bg-primary">${produto.linha_producao || '-'}</span></td>`;
        html += `<td><code class="clickable-produto" data-cod="${produto.cod_produto}" style="cursor:pointer; text-decoration:underline;">${produto.cod_produto}</code></td>`;
        html += `<td class="clickable-produto" data-cod="${produto.cod_produto}" style="cursor:pointer;">${produto.nome_produto || '-'}</td>`;
        html += `<td class="text-end">${formatarNumero(produto.quantidade)}</td>`;
        html += `<td class="text-center">${formatarData(produto.data_prevista)}</td>`;
        html += '<td class="text-center">';

        // Botões de ação
        html += `<button class="btn btn-xs btn-outline-primary me-1" onclick="editarProgramacao(${produto.id})" title="Editar">`;
        html += '<i class="fas fa-edit"></i></button>';
        html += `<button class="btn btn-xs btn-outline-danger" onclick="excluirProgramacao(${produto.id})" title="Excluir">`;
        html += '<i class="fas fa-trash"></i></button>';

        html += '</td></tr>';
    });

    html += '</tbody></table></div>';

    $('#table-view').html(html);

    // ✅ Adicionar evento de clique nos produtos para abrir modal
    adicionarEventosClickProduto();
}

// ============================================================
// EVENTOS DE CLIQUE NO PRODUTO
// ============================================================

function adicionarEventosClickProduto() {
    $('.clickable-produto').on('click', function() {
        const codProduto = $(this).data('cod');
        console.log('[TABLE VIEW] Clicou no produto:', codProduto);

        // Usar data atual como referência
        const hoje = new Date().toISOString().split('T')[0];

        // Abrir modal (função já existe no programacao-linhas.js ou necessidade-producao.js)
        if (typeof abrirModalSeparacoesProduto === 'function') {
            abrirModalSeparacoesProduto(codProduto, hoje);
        } else {
            alert('Função abrirModalSeparacoesProduto não encontrada. Verifique se os scripts estão carregados.');
        }
    });
}

// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

function formatarNumero(num) {
    if (!num) return '0';
    return parseFloat(num).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatarData(dataISO) {
    if (!dataISO) return '-';
    const [ano, mes, dia] = dataISO.split('-');
    return `${dia}/${mes}/${ano}`;
}

// ============================================================
// FUNÇÕES DE EDIÇÃO E EXCLUSÃO
// ============================================================

function editarProgramacao(id) {
    console.log('[TABLE VIEW] Editar programação ID:', id);
    // TODO: Implementar modal de edição
    alert(`Editar programação ID ${id}\n(Função a ser implementada)`);
}

function excluirProgramacao(id) {
    if (!confirm('Deseja realmente excluir esta programação?')) {
        return;
    }

    console.log('[TABLE VIEW] Excluir programação ID:', id);

    // TODO: Chamar API de exclusão
    fetch(`/manufatura/recursos/api/programacao/${id}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert('Programação excluída com sucesso!');
            // Recarregar dados
            carregarProgramacaoLinhas();
        } else {
            alert('Erro ao excluir: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('[TABLE VIEW] Erro ao excluir:', error);
        alert('Erro ao excluir programação');
    });
}

console.log('[TABLE VIEW] Script carregado');
