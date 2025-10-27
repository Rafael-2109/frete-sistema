// ==================================================
// NECESSIDADE DE PRODUÇÃO - SCRIPT PRINCIPAL
// ==================================================

let dadosCompletos = [];

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

    $('#btn-calcular').on('click', calcularNecessidade);
    $('#filtro-produto').on('keypress', e => e.which === 13 && calcularNecessidade());
    $('.col-toggle').on('change', () => { aplicarVisibilidadeColunas(); salvarPreferenciasColunas(); });
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
// CÁLCULO DE NECESSIDADE
// ============================================================

function calcularNecessidade() {
    const mes = $('#filtro-mes').val();
    const ano = $('#filtro-ano').val();
    const cod_produto = $('#filtro-produto').val().trim();

    $('#loading-spinner').removeClass('d-none');
    $('#tbody-necessidade').html('<tr><td colspan="100" class="text-center py-4"><div class="spinner-border spinner-border-sm text-success me-2"></div>Calculando...</td></tr>');

    $.ajax({
        url: '/manufatura/api/necessidade-producao/calcular',
        data: { mes, ano, cod_produto: cod_produto || undefined },
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
        const crit = calcularCriticidade(item.necessidade_producao, item.estoque_atual);
        const classCrit = crit === 'Alta' ? 'badge-alta' : crit === 'Média' ? 'badge-media' : 'badge-baixa';

        html += `<tr>
            <td class="sticky-col-codigo"><strong>${item.cod_produto}</strong></td>
            <td class="sticky-col-produto">
                <div class="d-flex align-items-center gap-2">
                    <div class="flex-grow-1">
                        ${item.nome_produto}${item.codigos_relacionados.length > 1 ? `<br><small class="text-muted"><i class="fas fa-link me-1"></i>${item.codigos_relacionados.join(', ')}</small>` : ''}
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
            <td class="text-end col-previsao">${formatarNumero(item.previsao_vendas)}</td>
            <td class="text-end col-pedidos">${formatarNumero(item.pedidos_inseridos)}</td>
            <td class="text-end col-carteira">${formatarNumero(item.carteira_pedidos)}</td>
            <td class="text-end col-saldo"><strong>${formatarNumero(item.saldo_vendas)}</strong></td>
            <td class="text-end col-estoque">${formatarNumero(item.estoque_atual)}</td>
            <td class="text-end col-programacao">${formatarNumero(item.programacao_producao)}</td>
            <td class="text-end col-necessidade ${item.necessidade_producao > 0 ? 'numero-positivo' : 'numero-zero'}"><strong>${formatarNumero(item.necessidade_producao)}</strong></td>
            <td class="text-center col-criticidade"><span class="badge-necessidade ${classCrit}">${crit}</span></td>`;

        for (let i = 0; i <= 60; i++) {
            const dia = item.projecao[i];
            if (dia) {
                const cls = dia.saldo_final < 0 ? 'negativo' : dia.saldo_final === 0 ? 'zero' : 'positivo';
                html += `<td class="col-projecao col-projecao-d${i} ${cls}">${formatarNumero(dia.saldo_final)}</td>`;
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
    $('.col-previsao').toggle($('#col-previsao').is(':checked'));
    $('.col-pedidos').toggle($('#col-pedidos').is(':checked'));
    $('.col-carteira').toggle($('#col-carteira').is(':checked'));
    $('.col-saldo').toggle($('#col-saldo').is(':checked'));
    $('.col-estoque').toggle($('#col-estoque').is(':checked'));
    $('.col-programacao').toggle($('#col-programacao').is(':checked'));
    $('.col-necessidade').toggle($('#col-necessidade').is(':checked'));
    $('.col-criticidade').toggle($('#col-criticidade').is(':checked'));

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
        $('.col-toggle').each(function() {
            const v = $(this).val();
            if (p.hasOwnProperty(v)) $(this).prop('checked', p[v]);
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

    const todosMenus = document.querySelectorAll('.menu-acoes-lista');

    // Fechar todos os outros menus
    todosMenus.forEach(m => {
        if (m.id !== 'menu-' + codProduto) {
            m.style.display = 'none';
        }
    });

    // Toggle do menu atual
    if (menu.style.display === 'none' || menu.style.display === '') {
        // Posicionar dropdown de forma inteligente
        posicionarDropdown(btn, menu);
        menu.style.display = 'block';
    } else {
        menu.style.display = 'none';
    }
}

function posicionarDropdown(btn, menu) {
    const btnRect = btn.getBoundingClientRect();
    const menuHeight = 200; // Altura estimada do menu
    const windowHeight = window.innerHeight;
    const spaceBelow = windowHeight - btnRect.bottom;
    const spaceAbove = btnRect.top;

    // Decidir se abre para cima ou para baixo
    if (spaceBelow < menuHeight && spaceAbove > spaceBelow) {
        // Abrir para CIMA
        menu.style.bottom = (windowHeight - btnRect.top) + 'px';
        menu.style.top = 'auto';
    } else {
        // Abrir para BAIXO (padrão)
        menu.style.top = (btnRect.bottom + 5) + 'px';
        menu.style.bottom = 'auto';
    }

    // Posição horizontal (sempre à direita do botão)
    menu.style.right = (window.innerWidth - btnRect.right) + 'px';
    menu.style.left = 'auto';
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
// UTILITÁRIOS
// ============================================================

function calcularCriticidade(nec, est) {
    return nec <= 0 ? 'Baixa' : nec > est * 0.5 ? 'Alta' : 'Média';
}

function formatarNumero(num) {
    return parseFloat(num || 0).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
