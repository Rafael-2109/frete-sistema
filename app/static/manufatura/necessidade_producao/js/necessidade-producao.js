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

    // 🚀 OTIMIZAÇÃO: Usar endpoint batch com chunking para >200 produtos
    const codProdutos = dados.map(item => item.cod_produto);
    const BATCH_SIZE = 200; // Limite do backend

    console.log(`🚀 [OTIMIZAÇÃO] Buscando ${codProdutos.length} projeções em BATCH`);

    // Dividir em chunks de 200
    const chunks = [];
    for (let i = 0; i < codProdutos.length; i += BATCH_SIZE) {
        chunks.push(codProdutos.slice(i, i + BATCH_SIZE));
    }

    console.log(`📦 Dividido em ${chunks.length} batches de até ${BATCH_SIZE} produtos`);

    // ✅ Obter CSRF token (necessário para POST requests)
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    if (!csrfToken) {
        console.error('❌ CSRF token não encontrado!');
        alert('Erro de segurança: Token CSRF não encontrado. Recarregue a página (F5).');
        dados.forEach(item => { item.projecao = []; });
        dadosCompletos = dados;
        renderizarTabela(dados);
        return;
    }

    // Buscar todos os chunks em paralelo
    const requests = chunks.map(chunk => {
        return $.ajax({
            url: '/manufatura/api/necessidade-producao/projecoes-batch',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': csrfToken  // ✅ Enviar CSRF token
            },
            data: JSON.stringify({
                cod_produtos: chunk,
                dias: 60
            })
        });
    });

    // Aguardar todas as requisições
    Promise.all(requests)
        .then(resultados => {
            console.log(`✅ ${resultados.length} batches recebidos com sucesso!`);

            // Combinar todos os resultados
            const projecoesBatch = {};
            resultados.forEach(resultado => {
                Object.assign(projecoesBatch, resultado);
            });

            console.log(`✅ Total de projeções combinadas: ${Object.keys(projecoesBatch).length}`);

            // Mapear projeções de volta para os produtos
            dados.forEach(item => {
                const projecaoProduto = projecoesBatch[item.cod_produto];
                if (projecaoProduto && projecaoProduto.projecao) {
                    item.projecao = projecaoProduto.projecao;
                } else {
                    item.projecao = [];
                }
            });

            dadosCompletos = dados;
            renderizarTabela(dados);
        })
        .catch(error => {
            console.error('❌ Erro ao buscar projeções batch:', error);

            if (error.responseJSON) {
                console.error('🐛 [DEBUG] Erro do servidor:', error.responseJSON);
                alert(`Erro: ${error.responseJSON.erro || 'Erro desconhecido'}`);
            } else {
                alert(`Erro ao buscar projeções: ${error.statusText || 'Erro desconhecido'}`);
            }

            // Fallback: atribuir projeção vazia para todos
            dados.forEach(item => { item.projecao = []; });
            dadosCompletos = dados;
            renderizarTabela(dados);
        });
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

/**
 * Formata data no formato YYYY-MM-DD para DD/MM/YYYY SEM problemas de timezone
 * @param {string} dataISO - Data no formato YYYY-MM-DD
 * @returns {string} Data formatada em DD/MM/YYYY
 */
function formatarDataSemTimezone(dataISO) {
    if (!dataISO) return '-';

    // Extrair componentes da string diretamente (sem criar objeto Date)
    const [ano, mes, dia] = dataISO.split('-');

    // Retornar no formato DD/MM/YYYY
    return `${dia}/${mes}/${ano}`;
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
    // ✅ 1. Mostrar código + nome no título
    $('#modal-separacoes-titulo').text(`${codProduto} - ${dados.nome_produto || ''}`);

    let html = '';

    // ============================================================
    // 1. TABELA HORIZONTAL DE MOVIMENTAÇÕES
    // ============================================================
    html += '<div class="table-responsive"><table class="table table-sm table-bordered table-hover">';
    html += '<thead><tr><th class="text-start" style="min-width: 120px;">Movimentação</th>';

    dados.dias.forEach(dia => {
        // ✅ 2. CORRIGIR TIMEZONE: Usar string diretamente sem new Date()
        const ehReferencia = dia.data === diaReferencia;
        const [ano, mes, diaNum] = dia.data.split('-');  // "2025-01-10" → ["2025", "01", "10"]
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
    // 2. ACCORDION - FORMULÁRIO ADICIONAR PROGRAMAÇÃO
    // ============================================================
    html += '<hr class="my-3">';
    html += '<div class="accordion mb-3" id="accordion-form-programacao">';
    html += `
        <div class="accordion-item">
            <h2 class="accordion-header" id="heading-form-prog">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-form-prog">
                    <i class="fas fa-plus-circle me-2 text-success"></i>Adicionar Programação de Produção
                </button>
            </h2>
            <div id="collapse-form-prog" class="accordion-collapse collapse" data-bs-parent="#accordion-form-programacao">
                <div class="accordion-body">
                    ${renderizarFormularioProgramacaoInline(codProduto, dados.linhas_producao || [])}
                </div>
            </div>
        </div>
    </div>`;

    // ============================================================
    // 3. ACCORDION DE PEDIDOS
    // ============================================================
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
            // ✅ ADICIONAR: onclick na linha para abrir modal de detalhes
            const separacaoLoteId = ped.separacao_lote_id || '';
            html += `<tr onclick="abrirModalDetalhesSeparacao('${separacaoLoteId}')" style="cursor: pointer;" title="Clique para ver detalhes">`;
            html += `<td><strong>${ped.num_pedido}</strong></td>`;
            html += `<td><small>${ped.cnpj_cpf || '-'}</small></td>`;
            html += `<td>${ped.raz_social_red || '-'}</td>`;
            html += `<td class="text-end">${Math.round(ped.qtd).toLocaleString('pt-BR')}</td>`;
            html += `<td>${ped.expedicao ? formatarDataSemTimezone(ped.expedicao) : '-'}</td>`;
            html += `<td>${ped.agendamento ? formatarDataSemTimezone(ped.agendamento) : '-'}</td>`;
            html += `<td class="text-center">${ped.agendamento_confirmado ? '<span class="badge bg-success">Sim</span>' : '<span class="badge bg-secondary">Não</span>'}</td>`;
            html += `<td>${ped.data_entrega_pedido ? formatarDataSemTimezone(ped.data_entrega_pedido) : '-'}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
    } else {
        html += '<div class="alert alert-info mb-0"><i class="fas fa-info-circle me-2"></i>Nenhum pedido não sincronizado</div>';
    }
    html += '</div></div></div></div>';

    // ============================================================
    // 4. ACCORDION DE ESTRUTURA DO PRODUTO (BOM)
    // ============================================================
    html += '<div class="accordion mb-3" id="accordion-bom">';
    html += `
        <div class="accordion-item">
            <h2 class="accordion-header" id="heading-bom">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-bom">
                    <i class="fas fa-sitemap me-2"></i>Estrutura do Produto (Componentes)
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
    // 5. ACCORDION DE PROGRAMAÇÃO DE PRODUÇÃO (D0-D60)
    // ============================================================
    html += '<div class="accordion mb-3" id="accordion-programacao-producao">';
    html += renderizarAccordionProgramacao(dados.programacoes_linhas, codProduto);
    html += '</div>';

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
            const dataFormatada = formatarDataSemTimezone(data);  // ✅ CORRIGIDO: sem timezone

            html += `<tr><td class="fw-bold align-top">${dataFormatada}</td><td>`;

            // Empilhar programações verticalmente (divs) COM EDIÇÃO
            programacoes.forEach(prog => {
                const classeDestaque = prog.eh_produto_modal ? 'produto-destaque' : '';
                const temObs = prog.observacao_pcp && prog.observacao_pcp.trim();
                const iconeObs = temObs ? ` <i class="fas fa-comment text-muted ms-1" data-bs-toggle="tooltip" title="${prog.observacao_pcp}" style="cursor:help;"></i>` : '';
                const progId = prog.id || 0;

                html += `
                    <div class="p-2 mb-1 border rounded ${classeDestaque} programacao-item" data-prog-id="${progId}">
                        <div class="d-flex justify-content-between align-items-center gap-2">
                            <div class="flex-grow-1">
                                <strong>${prog.cod_produto}</strong> - ${prog.nome_produto || ''}${iconeObs}
                                ${prog.cliente_produto ? ` <small class="text-muted ms-2">| Cliente: ${prog.cliente_produto}</small>` : ''}
                            </div>
                            <div class="d-flex align-items-center gap-2">
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
                                </button>
                            </div>
                        </div>
                    </div>`;
            });

            html += '</td></tr>';
        });

        html += '</tbody></table></div></div></div>';
        index++;
    }

    // Ativar tooltips
    setTimeout(() => {
        const tooltipTriggerList = document.querySelectorAll('#accordion-programacao-producao [data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
    }, 100);

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
 * Renderiza formulário inline SIMPLIFICADO (dentro de accordion)
 */
function renderizarFormularioProgramacaoInline(codProduto, linhasProducao) {
    return `
        <form id="form-add-programacao-${codProduto}" class="row g-2">
            <input type="hidden" name="cod_produto" value="${codProduto}">

            <div class="col-md-2">
                <label for="data-prog-${codProduto}" class="form-label form-label-sm">Data <span class="text-danger">*</span></label>
                <input type="date" class="form-control form-control-sm" id="data-prog-${codProduto}" name="data_programacao" required>
            </div>

            <div class="col-md-3">
                <label for="linha-prog-${codProduto}" class="form-label form-label-sm">Linha <span class="text-danger">*</span></label>
                <select class="form-select form-select-sm" id="linha-prog-${codProduto}" name="linha_producao" required>
                    <option value="">Selecione...</option>
                    ${linhasProducao.map(l => `<option value="${l.linha}">${l.linha}</option>`).join('')}
                </select>
            </div>

            <div class="col-md-2">
                <label for="qtd-prog-${codProduto}" class="form-label form-label-sm">Quantidade <span class="text-danger">*</span></label>
                <input type="number" class="form-control form-control-sm" id="qtd-prog-${codProduto}" name="qtd_programada" step="0.001" min="0" required>
            </div>

            <div class="col-md-2">
                <label for="cliente-prog-${codProduto}" class="form-label form-label-sm">Cliente</label>
                <input type="text" class="form-control form-control-sm" id="cliente-prog-${codProduto}" name="cliente_produto">
            </div>

            <div class="col-md-3">
                <label for="obs-prog-${codProduto}" class="form-label form-label-sm">Observações PCP</label>
                <input type="text" class="form-control form-control-sm" id="obs-prog-${codProduto}" name="observacao_pcp">
            </div>

            <div class="col-12 text-end">
                <button type="submit" class="btn btn-success btn-sm">
                    <i class="fas fa-check me-1"></i>Adicionar Programação
                </button>
            </div>
        </form>
    `;
}

/**
 * Renderiza programação de produção COMPACTA (1 linha por item)
 * Cliente inline + Observações em tooltip
 */
function renderizarProgramacaoProducaoCompacta(programacoesLinhas, codProdutoModal) {
    if (!programacoesLinhas || Object.keys(programacoesLinhas).length === 0) {
        return '<div class="alert alert-warning m-3"><i class="fas fa-exclamation-triangle me-2"></i>Nenhuma programação encontrada para as linhas de produção deste produto (D0-D60)</div>';
    }

    let html = '<table class="table table-sm table-bordered table-hover mb-0">';
    html += '<thead class="table-light"><tr>';
    html += '<th style="width: 100px;">Data</th>';
    html += '<th style="width: 150px;">Linha</th>';
    html += '<th>Produto</th>';
    html += '<th style="width: 150px;">Cliente</th>';
    html += '<th class="text-end" style="width: 100px;">Qtd</th>';
    html += '</tr></thead><tbody>';

    // Coletar todas as programações e ordenar por data + linha
    const todasProgramacoes = [];
    for (const [linha, dadosLinha] of Object.entries(programacoesLinhas)) {
        const datas = dadosLinha.datas || {};
        for (const [data, programacoes] of Object.entries(datas)) {
            programacoes.forEach(prog => {
                todasProgramacoes.push({
                    data,
                    linha,
                    ...prog
                });
            });
        }
    }

    // Ordenar por data + linha
    todasProgramacoes.sort((a, b) => {
        if (a.data !== b.data) return a.data.localeCompare(b.data);
        return a.linha.localeCompare(b.linha);
    });

    // Renderizar todas as programações
    todasProgramacoes.forEach(prog => {
        const classeDestaque = prog.eh_produto_modal ? 'produto-destaque' : '';
        const dataFormatada = formatarDataSemTimezone(prog.data);  // ✅ CORRIGIDO: sem timezone
        const temObs = prog.observacao_pcp && prog.observacao_pcp.trim();

        html += `<tr class="${classeDestaque}">`;
        html += `<td class="text-center">${dataFormatada}</td>`;
        html += `<td><small>${prog.linha}</small></td>`;
        html += `<td>`;
        html += `<strong>${prog.cod_produto}</strong> - ${prog.nome_produto || ''}`;
        if (temObs) {
            html += ` <i class="fas fa-comment text-muted" data-bs-toggle="tooltip" title="${prog.observacao_pcp}" style="cursor:help;"></i>`;
        }
        html += `</td>`;
        html += `<td><small class="text-muted">${prog.cliente_produto || '-'}</small></td>`;
        html += `<td class="text-end"><span class="badge bg-success">${formatarNumero(prog.qtd_programada)}</span></td>`;
        html += '</tr>';
    });

    html += '</tbody></table>';

    // Ativar tooltips do Bootstrap
    setTimeout(() => {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
    }, 100);

    return html;
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

    // ✅ MANTER ORDEM HIERÁRQUICA do backend (não ordenar!)
    const componentes = dados.componentes;  // Já vem na ordem correta PAI → FILHOS
    const producaoSKU = dados.producao_produto_sku;

    // 🐛 DEBUG: Verificar se qtd_total está vindo do backend
    console.log('[BOM DEBUG] Componentes recebidos:', componentes);
    console.log('[BOM DEBUG] Primeiro componente:', componentes[0]);

    // Wrapper com scroll lateral
    let html = '<div class="table-bom-wrapper"><table class="table table-sm table-bordered table-hover mb-0 table-bom-fixed">';

    // HEADER
    html += '<thead class="table-light"><tr>';
    html += '<th class="col-fixed-codigo text-start">Código</th>';
    html += '<th class="col-fixed-nome text-start">Nome</th>';
    html += '<th class="text-end">Qtd. Est.</th>';
    html += '<th class="text-end">Estoque Atual</th>';

    // ✅ 3. Colunas D0-D60 com dd/mm
    const hoje = new Date();
    for (let i = 0; i <= 60; i++) {
        const dataProjecao = new Date(hoje);
        dataProjecao.setDate(hoje.getDate() + i);
        const dia = dataProjecao.getDate().toString().padStart(2, '0');
        const mes = (dataProjecao.getMonth() + 1).toString().padStart(2, '0');
        html += `<th class="text-end col-projecao" title="D${i}">${dia}/${mes}</th>`;
    }
    html += '</tr></thead><tbody>';

    // LINHAS DE COMPONENTES
    componentes.forEach(comp => {
        const ehIntermediario = comp.eh_intermediario;
        const classeIntermediario = ehIntermediario ? 'bg-warning bg-opacity-10' : '';  // ✅ Destaque visual
        const icone = ehIntermediario ? '<i class="fas fa-sitemap text-warning me-1"></i>' : '<i class="fas fa-cube text-muted me-1"></i>';
        const nivel = comp.nivel || 0;
        const indentacao = '&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(nivel);  // ✅ Indentação hierárquica
        const nomeCompleto = comp.nome_produto || '';
        const nomeExibido = nomeCompleto.length > 35 ? nomeCompleto.substring(0, 35) + '...' : nomeCompleto;

        html += `<tr class="${classeIntermediario}">`;
        html += `<td class="col-fixed-codigo text-start"><small>${comp.cod_produto}</small></td>`;
        // ✅ Tooltip + Indentação
        html += `<td class="col-fixed-nome text-start" title="${nomeCompleto}" data-bs-toggle="tooltip">${indentacao}${icone}<small>${nomeExibido}</small></td>`;

        // ✅ APENAS qtd_total (consumo acumulado)
        html += `<td class="text-end"><strong>${formatarNumeroDecimais(comp.qtd_total, 6)}</strong></td>`;

        if (modo === 'qtd') {
            // Estoque Atual
            const classeEstoque = comp.estoque_atual < 0 ? 'valor-negativo' : '';
            html += `<td class="text-end ${classeEstoque}">${formatarNumero(comp.estoque_atual)}</td>`;

            // Projeção D0-D60 em quantidade (fundo vermelho se negativo)
            for (let i = 0; i <= 60; i++) {
                const valor = comp.projecao[`D${i}`] || 0;
                const classeNegativo = valor < 0 ? 'valor-negativo' : '';
                html += `<td class="text-end col-projecao ${classeNegativo}">${formatarNumero(valor)}</td>`;
            }
        } else {
            // modo === 'prod': Qtd Prod. Possível
            const classeEstoque = comp.qtd_prod_possivel < 0 ? 'valor-negativo' : '';
            html += `<td class="text-end ${classeEstoque}">${formatarNumero(comp.qtd_prod_possivel)}</td>`;

            // Projeção em "qtd prod possível" (fundo vermelho se negativo)
            for (let i = 0; i <= 60; i++) {
                const estoqueProj = comp.projecao[`D${i}`] || 0;
                const qtdProdPossivel = comp.qtd_total > 0 ? estoqueProj / comp.qtd_total : 0;
                const classeNegativo = qtdProdPossivel < 0 ? 'valor-negativo' : '';
                html += `<td class="text-end col-projecao ${classeNegativo}">${formatarNumero(qtdProdPossivel)}</td>`;
            }
        }

        html += '</tr>';
    });

    // LINHA ESPECIAL: Produção Produto SKU (gargalo)
    html += '<tr class="table-warning fw-bold">';
    html += '<td class="col-fixed-codigo" colspan="2"><i class="fas fa-exclamation-triangle me-1"></i>Produção Produto SKU (Mínimo)</td>';
    html += `<td class="text-end">-</td>`;  // Qtd. Est.
    html += `<td class="text-end text-danger">${formatarNumero(producaoSKU)}</td>`;  // Estoque Atual

    // Coluna vazia para D0-D60
    for (let i = 0; i <= 60; i++) {
        html += '<td class="col-projecao">-</td>';
    }
    html += '</tr>';

    html += '</tbody></table></div>';

    $(`#tabela-bom-${codProduto}`).html(html);

    // ✅ Ativar tooltips do Bootstrap na tabela
    setTimeout(() => {
        const tooltipTriggerList = document.querySelectorAll('#tabela-bom-' + codProduto + ' [data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
    }, 100);
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

// ============================================================
// FUNÇÕES DE EDIÇÃO E EXCLUSÃO DE PROGRAMAÇÃO
// ============================================================

/**
 * Salva edição de programação (data ou quantidade)
 */
async function salvarEdicaoProgramacao(programacaoId, novaData, novaQtd) {
    try {
        console.log(`[EDITAR PROG] ID: ${programacaoId}, Data: ${novaData}, Qtd: ${novaQtd}`);

        // Preparar dados para enviar
        const dados = {};
        if (novaData) dados.data_programacao = novaData;
        if (novaQtd) dados.qtd_programada = parseFloat(novaQtd);

        // Enviar requisição PUT
        const response = await fetch(`/manufatura/api/necessidade-producao/editar-programacao/${programacaoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });

        const resultado = await response.json();

        if (resultado.erro) {
            alert(`Erro: ${resultado.erro}`);
            // Reverter campo para valor original (recarregar modal)
            return;
        }

        // Sucesso - mostrar feedback visual
        const item = document.querySelector(`.programacao-item[data-prog-id="${programacaoId}"]`);
        if (item) {
            item.classList.add('flash-success');
            setTimeout(() => item.classList.remove('flash-success'), 1500);
        }

        console.log(`✅ Programação ${programacaoId} atualizada com sucesso`);

    } catch (error) {
        console.error('[EDITAR PROG] Erro:', error);
        alert(`Erro ao salvar alteração: ${error.message}`);
    }
}

/**
 * Exclui uma programação de produção
 */
async function excluirProgramacao(programacaoId) {
    try {
        // Confirmação
        const confirmar = await Swal.fire({
            title: 'Confirmar exclusão?',
            text: 'Esta ação não poderá ser desfeita.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Sim, excluir',
            cancelButtonText: 'Cancelar'
        });

        if (!confirmar.isConfirmed) {
            return;
        }

        // Enviar requisição DELETE
        const response = await fetch(`/manufatura/api/necessidade-producao/excluir-programacao/${programacaoId}`, {
            method: 'DELETE'
        });

        const resultado = await response.json();

        if (resultado.erro) {
            Swal.fire('Erro', resultado.erro, 'error');
            return;
        }

        // Sucesso - remover item da UI com animação
        const item = document.querySelector(`.programacao-item[data-prog-id="${programacaoId}"]`);
        if (item) {
            item.style.transition = 'opacity 0.3s, transform 0.3s';
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            setTimeout(() => item.remove(), 300);
        }

        Swal.fire({
            icon: 'success',
            title: 'Excluído!',
            text: 'Programação removida com sucesso',
            timer: 2000,
            showConfirmButton: false
        });

        console.log(`✅ Programação ${programacaoId} excluída com sucesso`);

    } catch (error) {
        console.error('[EXCLUIR PROG] Erro:', error);
        Swal.fire('Erro', `Erro ao excluir: ${error.message}`, 'error');
    }
}

