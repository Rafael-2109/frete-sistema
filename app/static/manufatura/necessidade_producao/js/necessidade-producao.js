// ==================================================
// NECESSIDADE DE PRODUÇÃO - SCRIPT PRINCIPAL
// ==================================================

let dadosCompletos = [];
let ordenacaoAtual = {
    campo: null,
    direcao: 'asc' // 'asc' ou 'desc'
};

$(document).ready(function() {
    const anoAtual = new Date().getFullYear();
    const mesAtual = new Date().getMonth() + 1;

    for (let i = -1; i <= 1; i++) {
        const ano = anoAtual + i;
        $('#filtro-ano').append($('<option></option>').val(ano).text(ano).prop('selected', i === 0));
    }
    $('#filtro-mes').val(mesAtual);

    gerarHeadersProjecao();
    carregarPreferenciasColunas();
    carregarTamanhoFonte();
    carregarFiltrosOpcoes(); // ✅ NOVO: Carregar opções dos filtros

    $('#btn-calcular').on('click', calcularNecessidade);
    $('#btn-limpar-filtros').on('click', limparFiltros); // ✅ NOVO
    $('.col-toggle').on('change', () => { aplicarVisibilidadeColunas(); salvarPreferenciasColunas(); });

    // ✅ NOVO: Autocomplete de produto
    let autocompleteTimer;
    $('#filtro-produto-busca').on('input', function() {
        clearTimeout(autocompleteTimer);
        const termo = $(this).val().trim();

        if (termo.length < 2) {
            $('#autocomplete-list').removeClass('show').empty();
            $('#filtro-cod-produto').val('');
            return;
        }

        autocompleteTimer = setTimeout(() => buscarProdutosAutocomplete(termo), 300);
    });

    // ✅ NOVO: Filtros dependentes
    $('#filtro-linha, #filtro-marca, #filtro-mp, #filtro-embalagem').on('change', function() {
        carregarFiltrosOpcoes();
    });

    // ✅ Fechar autocomplete ao clicar fora
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.autocomplete-container').length) {
            $('#autocomplete-list').removeClass('show');
        }
    });

    // ✅ Event listeners para ordenação de colunas
    $(document).on('click', '.sortable', function() {
        const campo = $(this).data('field');
        if (campo) {
            ordenarTabela(campo);
        }
    });
});

// ============================================================
// SISTEMA DE TAMANHO DE FONTE
// ============================================================

function mudarTamanhoFonte(tamanho) {
    // CORRIGIDO: Aplicar no elemento HTML para que as CSS Variables funcionem globalmente
    const htmlElement = document.documentElement;

    // Remove todas as classes de tamanho
    htmlElement.classList.remove('size-small', 'size-medium', 'size-large');

    // Adiciona a classe do tamanho selecionado (exceto very-small que é o padrão)
    if (tamanho !== 'very-small') {
        htmlElement.classList.add(`size-${tamanho}`);
    }

    // Atualiza botões ativos
    document.querySelectorAll('.btn-size').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.size === tamanho) {
            btn.classList.add('active');
        }
    });

    // Salva preferência
    localStorage.setItem('necessidade_tamanho_fonte', tamanho);

    console.log(`✅ Tamanho alterado para: ${tamanho}`);
    console.log(`📊 Classes no HTML:`, htmlElement.className);
}

function carregarTamanhoFonte() {
    const tamanhoSalvo = localStorage.getItem('necessidade_tamanho_fonte') || 'very-small';
    console.log(`📂 Carregando tamanho salvo: ${tamanhoSalvo}`);

    // Garante que a função execute após o DOM estar pronto
    setTimeout(() => {
        mudarTamanhoFonte(tamanhoSalvo);
    }, 100);
}

// ============================================================
// GERAÇÃO DE HEADERS DE PROJEÇÃO D0-D60
// ============================================================

function gerarHeadersProjecao() {
    const thead = $('#thead-row');
    const acoesCol = thead.find('th:last').remove();

    const hoje = new Date();
    const diasSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

    for (let i = 0; i <= 60; i++) {
        const data = new Date(hoje);
        data.setDate(hoje.getDate() + i);

        const diaMes = data.getDate();
        const diaSemana = diasSemana[data.getDay()];
        const texto = `${diaMes}<br>${diaSemana}`;

        const th = $('<th></th>')
            .addClass(`col-projecao col-projecao-d${i} text-end`)
            .html(texto)
            .attr('title', data.toLocaleDateString('pt-BR'));

        thead.append(th);
    }
    thead.append(acoesCol);
}

// ============================================================
// AUTOCOMPLETE DE PRODUTOS
// ============================================================

function buscarProdutosAutocomplete(termo) {
    $.ajax({
        url: '/manufatura/api/necessidade-producao/autocomplete-produtos',
        data: { termo },
        success: (produtos) => {
            const list = $('#autocomplete-list');
            list.empty();

            if (!produtos || produtos.length === 0) {
                list.html('<div class="autocomplete-no-results">Nenhum produto encontrado</div>');
                list.addClass('show');
                return;
            }

            produtos.forEach(p => {
                const item = $(`
                    <div class="autocomplete-item" data-cod="${p.cod_produto}">
                        <strong>${p.cod_produto}</strong>
                        <small>${p.nome_produto}${p.linha_producao ? ` - ${p.linha_producao}` : ''}</small>
                    </div>
                `);

                item.on('click', function() {
                    $('#filtro-produto-busca').val(`${p.cod_produto} - ${p.nome_produto}`);
                    $('#filtro-cod-produto').val(p.cod_produto);
                    list.removeClass('show');
                });

                list.append(item);
            });

            list.addClass('show');
        },
        error: () => {
            $('#autocomplete-list').html('<div class="autocomplete-no-results">Erro ao buscar</div>').addClass('show');
        }
    });
}

// ============================================================
// FILTROS DEPENDENTES
// ============================================================

function carregarFiltrosOpcoes() {
    const filtrosAtuais = obterFiltrosAtuais();

    $.ajax({
        url: '/manufatura/api/necessidade-producao/filtros-opcoes',
        data: filtrosAtuais,
        success: (dados) => {
            // Salvar valores selecionados
            const linhaAtual = $('#filtro-linha').val();
            const marcaAtual = $('#filtro-marca').val();
            const mpAtual = $('#filtro-mp').val();
            const embalagemAtual = $('#filtro-embalagem').val();

            // Atualizar Linha de Produção
            $('#filtro-linha').html('<option value="">Linha Produção</option>');
            dados.linhas_producao.forEach(l => {
                $('#filtro-linha').append($('<option></option>').val(l).text(l));
            });
            if (linhaAtual && dados.linhas_producao.includes(linhaAtual)) {
                $('#filtro-linha').val(linhaAtual);
            }

            // Atualizar Marca
            $('#filtro-marca').html('<option value="">Marca</option>');
            dados.marcas.forEach(m => {
                $('#filtro-marca').append($('<option></option>').val(m).text(m));
            });
            if (marcaAtual && dados.marcas.includes(marcaAtual)) {
                $('#filtro-marca').val(marcaAtual);
            }

            // Atualizar MP
            $('#filtro-mp').html('<option value="">MP</option>');
            dados.mps.forEach(mp => {
                $('#filtro-mp').append($('<option></option>').val(mp).text(mp));
            });
            if (mpAtual && dados.mps.includes(mpAtual)) {
                $('#filtro-mp').val(mpAtual);
            }

            // Atualizar Embalagem
            $('#filtro-embalagem').html('<option value="">Embalagem</option>');
            dados.embalagens.forEach(e => {
                $('#filtro-embalagem').append($('<option></option>').val(e).text(e));
            });
            if (embalagemAtual && dados.embalagens.includes(embalagemAtual)) {
                $('#filtro-embalagem').val(embalagemAtual);
            }

            console.log('✅ Filtros atualizados:', dados);
        },
        error: (err) => {
            console.error('❌ Erro ao carregar filtros:', err);
        }
    });
}

function obterFiltrosAtuais() {
    return {
        linha_producao: $('#filtro-linha').val() || undefined,
        marca: $('#filtro-marca').val() || undefined,
        mp: $('#filtro-mp').val() || undefined,
        embalagem: $('#filtro-embalagem').val() || undefined
    };
}

function limparFiltros() {
    $('#filtro-produto-busca').val('');
    $('#filtro-cod-produto').val('');
    $('#filtro-linha').val('');
    $('#filtro-marca').val('');
    $('#filtro-mp').val('');
    $('#filtro-embalagem').val('');
    $('#autocomplete-list').removeClass('show');
    carregarFiltrosOpcoes(); // Recarregar todas as opções
}

// ============================================================
// CÁLCULO DE NECESSIDADE
// ============================================================

function calcularNecessidade() {
    const mes = $('#filtro-mes').val();
    const ano = $('#filtro-ano').val();
    const cod_produto = $('#filtro-cod-produto').val().trim(); // ✅ ALTERADO: usar hidden field
    const linha_producao = $('#filtro-linha').val();
    const marca = $('#filtro-marca').val();
    const mp = $('#filtro-mp').val();
    const embalagem = $('#filtro-embalagem').val();

    $('#loading-spinner').removeClass('d-none');
    $('#tbody-necessidade').html('<tr><td colspan="100" class="text-center py-4"><div class="spinner-border spinner-border-sm text-success me-2"></div>Calculando...</td></tr>');

    // ✅ Construir params com filtros
    const params = {
        mes,
        ano,
        cod_produto: cod_produto || undefined,
        linha_producao: linha_producao || undefined,
        marca: marca || undefined,
        mp: mp || undefined,
        embalagem: embalagem || undefined
    };

    $.ajax({
        url: '/manufatura/api/necessidade-producao/calcular',
        data: params,
        success: buscarProjecoesParaTodos,
        error: () => {
            $('#tbody-necessidade').html('<tr><td colspan="100" class="text-center text-danger py-4"><i class="fas fa-exclamation-triangle me-2"></i>Erro ao carregar</td></tr>');
            $('#loading-spinner').addClass('d-none');
        }
    });
}

function buscarProjecoesParaTodos(dados) {
    if (!dados || !dados.length) { renderizarTabela([]); return; }

    Promise.all(dados.map(item =>
        $.get('/manufatura/api/necessidade-producao/projecao-estoque', { cod_produto: item.cod_produto })
            .then(p => { item.projecao = p.projecao || []; return item; })
            .catch(() => { item.projecao = []; return item; })
    )).then(d => { dadosCompletos = d; renderizarTabela(d); });
}

// ============================================================
// RENDERIZAÇÃO DA TABELA
// ============================================================

function renderizarTabela(dados) {
    if (!dados || !dados.length) {
        $('#tbody-necessidade').html('<tr><td colspan="100" class="text-center text-muted py-4"><i class="fas fa-inbox me-2"></i>Nenhum produto encontrado</td></tr>');
        $('#total-produtos').text('0 produtos');
        $('#loading-spinner').addClass('d-none');
        return;
    }

    let html = '';
    dados.forEach(item => {
        // Calcular classes condicionais
        const classeSaldoDemanda = item.saldo_demanda < 0 ? 'text-danger' : item.saldo_demanda > 0 ? 'text-success' : '';
        const classeRuptura = item.ruptura_carteira < 0 ? 'text-danger fw-bold' : '';

        html += `<tr>
            <!-- 1. Código -->
            <td class="sticky-col-codigo"><strong>${item.cod_produto}</strong></td>

            <!-- 2. Produto -->
            <td class="sticky-col-produto">
                <div class="d-flex align-items-center gap-2">
                    <div class="flex-grow-1">
                        ${item.nome_produto || 'Nome não encontrado'}
                    </div>
                    <div class="dropdown-acoes-produto" style="position: relative;">
                        <button type="button" class="btn-menu-acoes" onclick="toggleDropdown(this, '${item.cod_produto}')">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <div class="menu-acoes-lista" id="menu-${item.cod_produto}" style="display: none;">
                            <a href="#" onclick="verProjecao('${item.cod_produto}'); fecharDropdown(); return false;">
                                <i class="fas fa-chart-line"></i> Mov. Previstas
                            </a>
                            <a href="#" onclick="verPedidos('${item.cod_produto}'); fecharDropdown(); return false;">
                                <i class="fas fa-clipboard-list"></i> Pedidos
                            </a>
                            <a href="#" onclick="abrirModalRecursosProdutivos('${item.cod_produto}'); fecharDropdown(); return false;">
                                <i class="fas fa-industry"></i> Recursos Produtivos
                            </a>
                        </div>
                    </div>
                </div>
            </td>

            <!-- 3. Linha de Produção -->
            <td class="text-center col-producao">${item.linha_producao || '-'}</td>

            <!-- 4. Marca -->
            <td class="text-center col-marca">${item.categoria_produto || '-'}</td>

            <!-- 5. Embalagem -->
            <td class="text-center col-embalagem">${item.tipo_embalagem || '-'}</td>

            <!-- 6. MP -->
            <td class="text-center col-mp">${item.tipo_materia_prima || '-'}</td>

            <!-- 7. Estoque -->
            <td class="text-end col-estoque">${formatarNumero(item.estoque_atual)}</td>

            <!-- 8. Previsão Vendas -->
            <td class="text-end col-previsao">${formatarNumero(item.previsao_vendas)}</td>

            <!-- 9. Pedidos Inseridos -->
            <td class="text-end col-pedidos">${formatarNumero(item.pedidos_inseridos)}</td>

            <!-- 10. Saldo Demanda (NOVO) -->
            <td class="text-end col-saldo-demanda ${classeSaldoDemanda}">${formatarNumero(item.saldo_demanda)}</td>

            <!-- 11. Carteira Pedidos -->
            <td class="text-end col-carteira">${formatarNumero(item.carteira_pedidos)}</td>

            <!-- 12. Ruptura Carteira (NOVO) -->
            <td class="text-end col-ruptura ${classeRuptura}">${formatarNumero(item.ruptura_carteira)}</td>

            <!-- 13. Carteira S/ Data (NOVO) -->
            <td class="text-end col-carteira-sem-data">${formatarNumero(item.carteira_sem_data)}</td>

            <!-- 14. Saldo Vendas Acumulada -->
            <td class="text-end col-saldo"><strong>${formatarNumero(item.saldo_vendas)}</strong></td>

            <!-- 15. Programação Produção -->
            <td class="text-end col-programacao">${formatarNumero(item.programacao_producao)}</td>

            <!-- 16. Necessidade C/ Previsão -->
            <td class="text-end col-necessidade ${item.necessidade_producao > 0 ? 'numero-positivo' : 'numero-zero'}"><strong>${formatarNumero(item.necessidade_producao)}</strong></td>`;

        for (let i = 0; i <= 60; i++) {
            const dia = item.projecao[i];
            if (dia && dia.data) {
                const cls = dia.saldo_final < 0 ? 'negativo' : dia.saldo_final === 0 ? 'zero' : 'positivo';
                // ✅ Adicionar onclick para abrir modal de separações
                html += `<td class="col-projecao col-projecao-d${i} ${cls} cursor-pointer"
                             onclick="abrirModalSeparacoesProduto('${item.cod_produto}', '${dia.data}')"
                             title="Clique para ver separações e pedidos">${formatarNumero(dia.saldo_final)}</td>`;
            } else {
                html += `<td class="col-projecao col-projecao-d${i}">-</td>`;
            }
        }

        html += `<td class="text-center">-</td></tr>`;
    });

    $('#tbody-necessidade').html(html);
    $('#total-produtos').text(`${dados.length} produto${dados.length > 1 ? 's' : ''}`);
    console.log('✅ Tabela renderizada com', dados.length, 'produtos');

    $('#loading-spinner').addClass('d-none');
    aplicarVisibilidadeColunas();
}

// ============================================================
// VISIBILIDADE DE COLUNAS
// ============================================================

function aplicarVisibilidadeColunas() {
    // Colunas de CadastroPalletizacao
    $('.col-embalagem').toggle($('#col-embalagem').is(':checked'));
    $('.col-mp').toggle($('#col-mp').is(':checked'));
    $('.col-marca').toggle($('#col-marca').is(':checked'));
    $('.col-producao').toggle($('#col-producao').is(':checked'));

    // Colunas de dados
    $('.col-estoque').toggle($('#col-estoque').is(':checked'));
    $('.col-previsao').toggle($('#col-previsao').is(':checked'));
    $('.col-pedidos').toggle($('#col-pedidos').is(':checked'));
    $('.col-saldo-demanda').toggle($('#col-saldo-demanda').is(':checked'));  // ✅ NOVO
    $('.col-carteira').toggle($('#col-carteira').is(':checked'));
    $('.col-ruptura').toggle($('#col-ruptura').is(':checked'));  // ✅ NOVO
    $('.col-carteira-sem-data').toggle($('#col-carteira-sem-data').is(':checked'));  // ✅ NOVO
    $('.col-saldo').toggle($('#col-saldo').is(':checked'));
    $('.col-programacao').toggle($('#col-programacao').is(':checked'));
    $('.col-necessidade').toggle($('#col-necessidade').is(':checked'));

    // Projeção D0-D60
    const mostrar = $('#col-projecao').is(':checked');
    for (let i = 0; i <= 60; i++) $('.col-projecao-d' + i).toggle(mostrar);
}

function selecionarTodasColunas() {
    $('.col-toggle').prop('checked', true);
    aplicarVisibilidadeColunas();
    salvarPreferenciasColunas();
}

function limparSelecaoColunas() {
    $('.col-toggle').prop('checked', false);
    aplicarVisibilidadeColunas();
    salvarPreferenciasColunas();
}

function salvarPreferenciasColunas() {
    const prefs = {};
    $('.col-toggle').each(function() { prefs[$(this).val()] = $(this).is(':checked'); });
    localStorage.setItem('necessidade_colunas', JSON.stringify(prefs));
}

function carregarPreferenciasColunas() {
    const prefs = localStorage.getItem('necessidade_colunas');

    if (prefs) {
        const p = JSON.parse(prefs);

        // ✅ Garantir que novas colunas sejam marcadas por padrão
        const novasColunas = ['embalagem', 'mp', 'marca', 'producao', 'saldo-demanda', 'ruptura', 'carteira-sem-data'];

        $('.col-toggle').each(function() {
            const v = $(this).val();
            if (p.hasOwnProperty(v)) {
                $(this).prop('checked', p[v]);
            } else if (novasColunas.includes(v)) {
                // Nova coluna não salva ainda - marcar como checked por padrão
                $(this).prop('checked', true);
            }
        });
        aplicarVisibilidadeColunas();
    }
}

// ============================================================
// DROPDOWN DE AÇÕES - SIMPLES E FUNCIONAL
// ============================================================

function toggleDropdown(btn, codProduto) {
    const menu = document.getElementById('menu-' + codProduto);

    if (!menu) {
        console.error('❌ Menu não encontrado! ID:', 'menu-' + codProduto);
        return;
    }

    console.log(`🔍 Toggle menu produto: ${codProduto}, display atual: ${menu.style.display}`);

    const todosMenus = document.querySelectorAll('.menu-acoes-lista');

    // Fechar todos os outros menus
    todosMenus.forEach(m => {
        if (m.id !== 'menu-' + codProduto) {
            m.style.display = 'none';
        }
    });

    // Toggle do menu atual
    if (menu.style.display === 'none' || menu.style.display === '') {
        console.log(`✅ Abrindo menu ${codProduto}...`);

        // ✅ SOLUÇÃO: Mover menu para fora da table-container (evita overflow)
        const dropdownContainer = document.getElementById('dropdown-container');
        if (dropdownContainer && menu.parentElement !== dropdownContainer) {
            dropdownContainer.appendChild(menu);
            console.log(`📦 Menu ${codProduto} movido para dropdown-container`);
        }

        // Posicionar dropdown de forma inteligente
        posicionarDropdown(btn, menu);
        menu.style.display = 'block';
        console.log(`📊 Menu ${codProduto} aberto! Display: ${menu.style.display}`);
    } else {
        console.log(`❌ Fechando menu ${codProduto}...`);
        menu.style.display = 'none';
    }
}

function posicionarDropdown(btn, menu) {
    const btnRect = btn.getBoundingClientRect();
    const menuWidth = 200; // Largura estimada do menu
    const menuHeight = 150; // Altura estimada do menu
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    // Calcular espaços disponíveis
    const spaceBelow = windowHeight - btnRect.bottom;
    const spaceAbove = btnRect.top;
    const spaceRight = windowWidth - btnRect.right;
    const spaceLeft = btnRect.left;

    // ✅ POSIÇÃO VERTICAL: Decidir se abre para cima ou para baixo
    if (spaceBelow < menuHeight && spaceAbove > spaceBelow) {
        // Abrir para CIMA
        menu.style.bottom = (windowHeight - btnRect.top + 5) + 'px';
        menu.style.top = 'auto';
    } else {
        // Abrir para BAIXO (padrão)
        menu.style.top = (btnRect.bottom + 5) + 'px';
        menu.style.bottom = 'auto';
    }

    // ✅ POSIÇÃO HORIZONTAL: Decidir se abre à esquerda ou direita do botão
    if (spaceRight < menuWidth && spaceLeft > menuWidth) {
        // Abrir à ESQUERDA do botão
        menu.style.left = 'auto';
        menu.style.right = (windowWidth - btnRect.left) + 'px';
    } else {
        // Abrir à DIREITA do botão (padrão) ou alinhado à direita do botão
        menu.style.left = 'auto';
        menu.style.right = (windowWidth - btnRect.right) + 'px';
    }

    console.log(`📍 Menu posicionado: top=${menu.style.top}, bottom=${menu.style.bottom}, right=${menu.style.right}`);
}

function fecharDropdown() {
    const todosMenus = document.querySelectorAll('.menu-acoes-lista');
    todosMenus.forEach(m => m.style.display = 'none');
}

// Fechar dropdown ao clicar fora
document.addEventListener('click', function(event) {
    if (!event.target.closest('.dropdown-acoes-produto')) {
        fecharDropdown();
    }
});

// ============================================================
// ORDENAÇÃO DE COLUNAS
// ============================================================

function ordenarTabela(campo) {
    console.log(`🔄 Ordenando por: ${campo}`);

    // Se clicar na mesma coluna, inverte a direção
    if (ordenacaoAtual.campo === campo) {
        ordenacaoAtual.direcao = ordenacaoAtual.direcao === 'asc' ? 'desc' : 'asc';
    } else {
        // Nova coluna, sempre começa em ascendente
        ordenacaoAtual.campo = campo;
        ordenacaoAtual.direcao = 'asc';
    }

    // Ordenar dados
    dadosCompletos.sort((a, b) => {
        let valorA = a[campo];
        let valorB = b[campo];

        // Tratar valores null/undefined como string vazia para campos de texto
        if (valorA === null || valorA === undefined) valorA = '';
        if (valorB === null || valorB === undefined) valorB = '';

        // Detectar tipo de dado
        const isNumero = typeof valorA === 'number' || !isNaN(parseFloat(valorA));

        let comparacao = 0;
        if (isNumero) {
            // Comparação numérica
            const numA = parseFloat(valorA) || 0;
            const numB = parseFloat(valorB) || 0;
            comparacao = numA - numB;
        } else {
            // Comparação alfabética (case-insensitive)
            const strA = String(valorA).toLowerCase();
            const strB = String(valorB).toLowerCase();
            comparacao = strA.localeCompare(strB, 'pt-BR');
        }

        return ordenacaoAtual.direcao === 'asc' ? comparacao : -comparacao;
    });

    // Atualizar ícones visuais
    atualizarIconesOrdenacao(campo, ordenacaoAtual.direcao);

    // Re-renderizar tabela
    renderizarTabela(dadosCompletos);
}

function atualizarIconesOrdenacao(campoAtivo, direcao) {
    // Resetar todos os ícones
    $('.sortable .sort-icon').removeClass('fa-sort-up fa-sort-down').addClass('fa-sort');

    // Atualizar ícone da coluna ativa
    const icone = $(`.sortable[data-field="${campoAtivo}"] .sort-icon`);
    icone.removeClass('fa-sort');
    icone.addClass(direcao === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
}

// ============================================================
// UTILITÁRIOS
// ============================================================

function formatarNumero(num) {
    return parseFloat(num || 0).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

// ============================================================
// MODAL DE SEPARAÇÕES E ESTOQUE (Reutilizado de programacao-linhas)
// ============================================================

async function abrirModalSeparacoesProduto(codProduto, diaClicado) {
    try {
        console.log(`[MODAL SEPARACOES] Abrindo para produto: ${codProduto}, dia: ${diaClicado}`);

        // Calcular período: 7 dias antes + dia + 7 dias depois
        const dataClicada = new Date(diaClicado);
        const dataInicio = new Date(dataClicada);
        dataInicio.setDate(dataInicio.getDate() - 7);
        const dataFim = new Date(dataClicada);
        dataFim.setDate(dataFim.getDate() + 7);

        // Buscar dados do backend
        const params = new URLSearchParams({
            cod_produto: codProduto,
            data_inicio: dataInicio.toISOString().split('T')[0],
            data_fim: dataFim.toISOString().split('T')[0],
            data_referencia: diaClicado
        });

        const response = await fetch(`/manufatura/recursos/api/separacoes-estoque?${params}`);
        const dados = await response.json();

        if (dados.erro) {
            throw new Error(dados.erro);
        }

        // Renderizar modal
        renderizarModalSeparacoes(dados, codProduto, diaClicado);

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('modalSeparacoesProduto'));
        modal.show();

    } catch (error) {
        console.error('[MODAL SEPARACOES] Erro:', error);
        alert(`Erro ao carregar separações: ${error.message}`);
    }
}

function renderizarModalSeparacoes(dados, codProduto, diaReferencia) {
    $('#modal-separacoes-titulo').text(`${dados.nome_produto || codProduto}`);

    let html = '';

    // ============================================================
    // 1. TABELA HORIZONTAL DE MOVIMENTAÇÕES (MANTÉM COMO ESTAVA)
    // ============================================================
    html += '<div class="table-responsive"><table class="table table-sm table-bordered table-hover">';
    html += '<thead><tr><th class="text-start" style="min-width: 120px;">Movimentação</th>';

    dados.dias.forEach(dia => {
        const ehReferencia = dia.data === diaReferencia;
        const data = new Date(dia.data);
        const diaNum = data.getDate().toString().padStart(2, '0');
        const mes = (data.getMonth() + 1).toString().padStart(2, '0');
        const classe = ehReferencia ? 'table-warning fw-bold' : '';
        html += `<th class="text-center ${classe}" style="min-width: 70px;">${diaNum}/${mes}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Linhas: Est. Inicial, Entradas, Saídas, Est. Final
    html += '<tr><td class="fw-bold bg-light">Est. Inicial</td>';
    dados.dias.forEach(dia => {
        const classe = dia.data === diaReferencia ? 'table-warning' : '';
        html += `<td class="text-center ${classe}">${Math.round(dia.est_inicial).toLocaleString('pt-BR')}</td>`;
    });
    html += '</tr>';

    html += '<tr><td class="fw-bold bg-light">Entradas</td>';
    dados.dias.forEach(dia => {
        const classe = dia.data === diaReferencia ? 'table-warning' : '';
        const valor = dia.entradas > 0 ? `<span class="text-success fw-bold">+${Math.round(dia.entradas).toLocaleString('pt-BR')}</span>` : '0';
        html += `<td class="text-center ${classe}">${valor}</td>`;
    });
    html += '</tr>';

    html += '<tr><td class="fw-bold bg-light">Saídas</td>';
    dados.dias.forEach(dia => {
        const classe = dia.data === diaReferencia ? 'table-warning' : '';
        const valor = dia.saidas > 0 ? `<span class="text-danger fw-bold">-${Math.round(dia.saidas).toLocaleString('pt-BR')}</span>` : '0';
        html += `<td class="text-center ${classe}">${valor}</td>`;
    });
    html += '</tr>';

    html += '<tr class="table-primary"><td class="fw-bold">Est. Final</td>';
    dados.dias.forEach(dia => {
        const classe = dia.data === diaReferencia ? 'table-warning fw-bold' : '';
        const valor = Math.round(dia.est_final);
        const cor = valor < 0 ? 'text-danger' : valor === 0 ? 'text-muted' : 'text-dark';
        html += `<td class="text-center fw-bold ${classe} ${cor}">${valor.toLocaleString('pt-BR')}</td>`;
    });
    html += '</tr>';
    html += '</tbody></table></div>';

    // ============================================================
    // 2. NOVO: ACCORDION DE PROGRAMAÇÃO DE PRODUÇÃO (D0-D60)
    // ============================================================
    html += '<hr class="my-4">';
    html += '<h6 class="text-primary mb-3"><i class="fas fa-calendar-alt me-2"></i>Programação de Produção (D0-D60)</h6>';
    html += '<div class="accordion mb-3" id="accordion-programacao-producao">';
    html += renderizarAccordionProgramacao(dados.programacoes_linhas, codProduto);
    html += '</div>';

    // ============================================================
    // 3. NOVO: ACCORDION DE ESTRUTURA DO PRODUTO (BOM)
    // ============================================================
    html += '<hr class="my-4">';
    html += '<div class="accordion mb-3" id="accordion-bom">';
    html += `
        <div class="accordion-item">
            <h2 class="accordion-header" id="heading-bom">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-bom">
                    <i class="fas fa-sitemap me-2"></i>Estrutura do Produto (BOM)
                </button>
            </h2>
            <div id="collapse-bom" class="accordion-collapse collapse" data-bs-parent="#accordion-bom">
                <div class="accordion-body">
                    <div class="d-flex justify-content-end mb-3">
                        <div class="btn-group btn-group-sm" role="group">
                            <input type="radio" class="btn-check" name="toggle-bom-${codProduto}" id="toggle-qtd-${codProduto}" checked>
                            <label class="btn btn-outline-primary" for="toggle-qtd-${codProduto}">Qtd Componentes</label>
                            <input type="radio" class="btn-check" name="toggle-bom-${codProduto}" id="toggle-prod-${codProduto}">
                            <label class="btn btn-outline-primary" for="toggle-prod-${codProduto}">Qtd Prod. Possível</label>
                        </div>
                    </div>
                    <div id="tabela-bom-${codProduto}" class="text-center py-3">
                        <div class="spinner-border text-primary" role="status"></div>
                        <p class="mt-2">Carregando estrutura...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>`;

    // ============================================================
    // 4. NOVO: FORMULÁRIO ADICIONAR PROGRAMAÇÃO
    // ============================================================
    html += '<hr class="my-4">';
    html += renderizarFormularioProgramacao(codProduto, dados.linhas_producao || []);

    // ============================================================
    // 5. NOVO: ACCORDION DE PEDIDOS (MOVIDO DE ONDE ESTAVA)
    // ============================================================
    html += '<hr class="my-4">';
    html += '<div class="accordion mb-3" id="accordion-pedidos-sep">';
    html += `
        <div class="accordion-item">
            <h2 class="accordion-header" id="heading-pedidos-sep">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-pedidos-sep">
                    <i class="fas fa-clipboard-list me-2"></i>Pedidos Não Sincronizados <span class="badge bg-success ms-2">${dados.pedidos ? dados.pedidos.length : 0}</span>
                </button>
            </h2>
            <div id="collapse-pedidos-sep" class="accordion-collapse collapse" data-bs-parent="#accordion-pedidos-sep">
                <div class="accordion-body p-0">`;

    if (dados.pedidos && dados.pedidos.length > 0) {
        html += '<div class="table-responsive"><table class="table table-sm table-bordered table-striped mb-0">';
        html += '<thead class="table-light"><tr>';
        html += '<th>Pedido</th><th>CNPJ</th><th>Cliente</th><th class="text-end">Qtd</th>';
        html += '<th>Expedição</th><th>Agendamento</th><th class="text-center">Confirmado</th><th>Dt. Entrega</th>';
        html += '</tr></thead><tbody>';

        dados.pedidos.forEach(ped => {
            html += '<tr>';
            html += `<td><strong>${ped.num_pedido}</strong></td>`;
            html += `<td><small>${ped.cnpj_cpf || '-'}</small></td>`;
            html += `<td>${ped.raz_social_red || '-'}</td>`;
            html += `<td class="text-end">${Math.round(ped.qtd).toLocaleString('pt-BR')}</td>`;
            html += `<td>${ped.expedicao ? new Date(ped.expedicao).toLocaleDateString('pt-BR') : '-'}</td>`;
            html += `<td>${ped.agendamento ? new Date(ped.agendamento).toLocaleDateString('pt-BR') : '-'}</td>`;
            html += `<td class="text-center">${ped.agendamento_confirmado ? '<span class="badge bg-success">Sim</span>' : '<span class="badge bg-secondary">Não</span>'}</td>`;
            html += `<td>${ped.data_entrega_pedido ? new Date(ped.data_entrega_pedido).toLocaleDateString('pt-BR') : '-'}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
    } else {
        html += '<div class="alert alert-info mb-0"><i class="fas fa-info-circle me-2"></i>Nenhum pedido não sincronizado</div>';
    }

    html += '</div></div></div></div>';

    $('#modal-separacoes-conteudo').html(html);

    // Listeners para BOM toggle e formulário
    configurarListenersBOM(codProduto);
    configurarListenersFormularioProgramacao(codProduto, dados.nome_produto);
}

// ============================================================
// FUNÇÕES AUXILIARES PARA NOVOS COMPONENTES DO MODAL
// ============================================================

/**
 * Renderiza accordion de programação de produção agrupado por linha
 * Estrutura: Dias nas LINHAS, produtos em divs empilhadas verticalmente
 */
function renderizarAccordionProgramacao(programacoesLinhas, codProdutoModal) {
    if (!programacoesLinhas || Object.keys(programacoesLinhas).length === 0) {
        return '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>Nenhuma programação encontrada para as linhas de produção deste produto (D0-D60)</div>';
    }

    let html = '';
    let index = 0;

    for (const [linha, dadosLinha] of Object.entries(programacoesLinhas)) {
        const totalProgramado = dadosLinha.total_programado || 0;
        const datas = dadosLinha.datas || {};
        const numDias = Object.keys(datas).length;

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading-prog-${index}">
                    <button class="accordion-button ${index === 0 ? '' : 'collapsed'}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#collapse-prog-${index}">
                        <div class="d-flex justify-content-between w-100 me-3">
                            <div><strong>${linha}</strong></div>
                            <div>
                                <span class="badge bg-primary me-2">Qtd programada do produto: ${formatarNumero(totalProgramado)}</span>
                                <span class="badge bg-secondary">${numDias} dias</span>
                            </div>
                        </div>
                    </button>
                </h2>
                <div id="collapse-prog-${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}"
                     data-bs-parent="#accordion-programacao-producao">
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
        const datasOrdenadas = Object.keys(datas).sort();

        datasOrdenadas.forEach(data => {
            const programacoes = datas[data];
            const dataFormatada = new Date(data).toLocaleDateString('pt-BR');

            html += `<tr><td class="fw-bold align-top">${dataFormatada}</td><td>`;

            // Empilhar programações verticalmente (divs)
            programacoes.forEach(prog => {
                const classeDestaque = prog.eh_produto_modal ? 'produto-destaque' : '';
                html += `
                    <div class="p-2 mb-1 border rounded ${classeDestaque}">
                        <div class="d-flex justify-content-between">
                            <div>
                                <strong>${prog.cod_produto}</strong> - ${prog.nome_produto || ''}
                                ${prog.cliente_produto ? `<br><small class="text-muted">Cliente: ${prog.cliente_produto}</small>` : ''}
                            </div>
                            <div class="text-end">
                                <span class="badge bg-success">${formatarNumero(prog.qtd_programada)}</span>
                            </div>
                        </div>
                        ${prog.observacao_pcp ? `<small class="text-muted"><i class="fas fa-comment me-1"></i>${prog.observacao_pcp}</small>` : ''}
                    </div>`;
            });

            html += '</td></tr>';
        });

        html += '</tbody></table></div></div></div>';
        index++;
    }

    return html;
}

/**
 * Renderiza formulário para adicionar programação de produção
 */
function renderizarFormularioProgramacao(codProduto, linhasProducao) {
    return `
        <div class="card border-success">
            <div class="card-header bg-success text-white">
                <i class="fas fa-plus me-2"></i>Adicionar Programação de Produção
            </div>
            <div class="card-body">
                <form id="form-add-programacao-${codProduto}" class="row g-3">
                    <input type="hidden" name="cod_produto" value="${codProduto}">

                    <div class="col-md-3">
                        <label for="data-prog-${codProduto}" class="form-label">Data Programação <span class="text-danger">*</span></label>
                        <input type="date" class="form-control form-control-sm" id="data-prog-${codProduto}" name="data_programacao" required>
                    </div>

                    <div class="col-md-3">
                        <label for="linha-prog-${codProduto}" class="form-label">Linha de Produção <span class="text-danger">*</span></label>
                        <select class="form-select form-select-sm" id="linha-prog-${codProduto}" name="linha_producao" required>
                            <option value="">Selecione...</option>
                            ${linhasProducao.map(l => `<option value="${l.linha}">${l.linha}</option>`).join('')}
                        </select>
                    </div>

                    <div class="col-md-2">
                        <label for="qtd-prog-${codProduto}" class="form-label">Quantidade <span class="text-danger">*</span></label>
                        <input type="number" class="form-control form-control-sm" id="qtd-prog-${codProduto}" name="qtd_programada" step="0.001" min="0" required>
                    </div>

                    <div class="col-md-2">
                        <label for="cliente-prog-${codProduto}" class="form-label">Cliente/Marca</label>
                        <input type="text" class="form-control form-control-sm" id="cliente-prog-${codProduto}" name="cliente_produto">
                    </div>

                    <div class="col-md-2 d-flex align-items-end">
                        <button type="submit" class="btn btn-success btn-sm w-100">
                            <i class="fas fa-check me-1"></i>Adicionar
                        </button>
                    </div>

                    <div class="col-12">
                        <label for="obs-prog-${codProduto}" class="form-label">Observações PCP</label>
                        <textarea class="form-control form-control-sm" id="obs-prog-${codProduto}" name="observacao_pcp" rows="2"></textarea>
                    </div>
                </form>
            </div>
        </div>
    `;
}

/**
 * Configura listeners do toggle de BOM e carrega dados ao expandir
 */
function configurarListenersBOM(codProduto) {
    const collapseId = `#collapse-bom`;
    let dadosBOM = null;
    let modoAtual = 'qtd'; // 'qtd' ou 'prod'

    // Listener para quando o accordion abrir
    $(collapseId).on('show.bs.collapse', async function() {
        if (dadosBOM === null) {
            // Buscar BOM pela primeira vez
            try {
                const response = await fetch(`/manufatura/api/necessidade-producao/bom-recursiva-estoque?cod_produto=${codProduto}`);
                dadosBOM = await response.json();

                if (dadosBOM.erro) {
                    $(`#tabela-bom-${codProduto}`).html(`<div class="alert alert-danger">${dadosBOM.erro}</div>`);
                } else {
                    renderizarTabelaBOM(codProduto, dadosBOM, modoAtual);
                }
            } catch (error) {
                console.error('[BOM] Erro:', error);
                $(`#tabela-bom-${codProduto}`).html(`<div class="alert alert-danger">Erro ao carregar BOM: ${error.message}</div>`);
            }
        }
    });

    // Listener para toggle de modo
    $(`input[name="toggle-bom-${codProduto}"]`).on('change', function() {
        modoAtual = this.id.includes('qtd') ? 'qtd' : 'prod';
        if (dadosBOM) {
            renderizarTabelaBOM(codProduto, dadosBOM, modoAtual);
        }
    });
}

/**
 * Renderiza tabela de BOM com scroll lateral (código e nome fixos)
 */
function renderizarTabelaBOM(codProduto, dados, modo) {
    if (!dados.componentes || dados.componentes.length === 0) {
        $(`#tabela-bom-${codProduto}`).html(`<div class="alert alert-info">${dados.mensagem || 'Nenhum componente encontrado'}</div>`);
        return;
    }

    const componentes = dados.componentes;
    const producaoSKU = dados.producao_produto_sku;

    // Wrapper com scroll lateral
    let html = '<div class="table-bom-wrapper"><table class="table table-sm table-bordered table-hover mb-0 table-bom-fixed">';

    // HEADER
    html += '<thead class="table-light"><tr>';
    html += '<th class="col-fixed-codigo">Código</th>';
    html += '<th class="col-fixed-nome">Nome</th>';
    html += '<th class="text-end">Qtd Utilizada</th>';
    html += '<th class="text-end">Estoque Atual</th>';

    // Colunas D0-D60
    for (let i = 0; i <= 60; i++) {
        html += `<th class="text-end col-projecao">D${i}</th>`;
    }
    html += '</tr></thead><tbody>';

    // LINHAS DE COMPONENTES
    componentes.forEach(comp => {
        const nivel = comp.nivel || 0;
        const indentacao = '&nbsp;&nbsp;'.repeat(nivel * 2);
        const icone = comp.eh_intermediario ? '<i class="fas fa-sitemap text-warning me-1"></i>' : '<i class="fas fa-cube text-muted me-1"></i>';

        html += '<tr>';
        html += `<td class="col-fixed-codigo"><small>${comp.cod_produto}</small></td>`;
        html += `<td class="col-fixed-nome">${indentacao}${icone}<small>${comp.nome_produto}</small></td>`;
        html += `<td class="text-end">${formatarNumeroDecimais(comp.qtd_utilizada, 6)}</td>`;

        if (modo === 'qtd') {
            html += `<td class="text-end">${formatarNumero(comp.estoque_atual)}</td>`;
            // Projeção D0-D60 em quantidade
            for (let i = 0; i <= 60; i++) {
                const valor = comp.projecao[`D${i}`] || 0;
                const cor = valor < 0 ? 'text-danger fw-bold' : '';
                html += `<td class="text-end col-projecao ${cor}">${formatarNumero(valor)}</td>`;
            }
        } else {
            // modo === 'prod': Qtd Prod. Possível
            html += `<td class="text-end text-primary fw-bold">${formatarNumero(comp.qtd_prod_possivel)}</td>`;
            // Projeção em "qtd prod possível"
            for (let i = 0; i <= 60; i++) {
                const estoqueProj = comp.projecao[`D${i}`] || 0;
                const qtdProdPossivel = comp.qtd_utilizada > 0 ? estoqueProj / comp.qtd_utilizada : 0;
                const cor = qtdProdPossivel < 0 ? 'text-danger fw-bold' : 'text-primary';
                html += `<td class="text-end col-projecao ${cor}">${formatarNumero(qtdProdPossivel)}</td>`;
            }
        }

        html += '</tr>';
    });

    // LINHA ESPECIAL: Produção Produto SKU (gargalo)
    html += '<tr class="table-warning fw-bold">';
    html += '<td class="col-fixed-codigo" colspan="2"><i class="fas fa-exclamation-triangle me-1"></i>Produção Produto SKU (Mínimo)</td>';
    html += `<td class="text-end">-</td>`;
    html += `<td class="text-end text-danger">${formatarNumero(producaoSKU)}</td>`;

    // Coluna vazia para D0-D60
    for (let i = 0; i <= 60; i++) {
        html += '<td class="col-projecao">-</td>';
    }
    html += '</tr>';

    html += '</tbody></table></div>';

    $(`#tabela-bom-${codProduto}`).html(html);
}

/**
 * Configura listeners do formulário de adicionar programação
 */
function configurarListenersFormularioProgramacao(codProduto, nomeProduto) {
    $(`#form-add-programacao-${codProduto}`).on('submit', async function(e) {
        e.preventDefault();

        const formData = {
            cod_produto: codProduto,
            data_programacao: $(`#data-prog-${codProduto}`).val(),
            linha_producao: $(`#linha-prog-${codProduto}`).val(),
            qtd_programada: parseFloat($(`#qtd-prog-${codProduto}`).val()),
            cliente_produto: $(`#cliente-prog-${codProduto}`).val(),
            observacao_pcp: $(`#obs-prog-${codProduto}`).val()
        };

        // Validação básica
        if (!formData.data_programacao || !formData.linha_producao || !formData.qtd_programada || formData.qtd_programada <= 0) {
            alert('Por favor, preencha todos os campos obrigatórios corretamente');
            return;
        }

        try {
            const response = await fetch('/manufatura/api/necessidade-producao/adicionar-programacao', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const resultado = await response.json();

            if (resultado.erro) {
                alert(`Erro: ${resultado.erro}`);
            } else {
                // Sucesso - Recarregar modal de forma suave
                Swal.fire({
                    icon: 'success',
                    title: 'Programação adicionada!',
                    text: resultado.mensagem,
                    timer: 2000,
                    showConfirmButton: false
                });

                // Limpar formulário
                $(`#form-add-programacao-${codProduto}`)[0].reset();

                // Reload suave: re-buscar dados e re-renderizar
                setTimeout(async () => {
                    const params = new URLSearchParams({
                        cod_produto: codProduto,
                        data_inicio: new Date(Date.now() - 7*24*60*60*1000).toISOString().split('T')[0],
                        data_fim: new Date(Date.now() + 7*24*60*60*1000).toISOString().split('T')[0],
                        data_referencia: new Date().toISOString().split('T')[0]
                    });

                    const resp = await fetch(`/manufatura/recursos/api/separacoes-estoque?${params}`);
                    const dadosAtualizados = await response.json();

                    // Re-renderizar apenas o accordion de programação
                    const htmlNovo = renderizarAccordionProgramacao(dadosAtualizados.programacoes_linhas, codProduto);
                    $('#accordion-programacao-producao').html(htmlNovo);
                }, 2100);
            }
        } catch (error) {
            console.error('[ADD PROGRAMACAO] Erro:', error);
            alert(`Erro ao adicionar programação: ${error.message}`);
        }
    });
}

/**
 * Formata número com até 6 casas decimais (formato brasileiro)
 */
function formatarNumeroDecimais(num, decimais = 6) {
    return parseFloat(num || 0).toLocaleString('pt-BR', {
        minimumFractionDigits: 0,
        maximumFractionDigits: decimais
    });
}
