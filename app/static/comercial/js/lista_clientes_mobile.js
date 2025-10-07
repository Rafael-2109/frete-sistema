/**
 * LISTA CLIENTES - MOBILE JAVASCRIPT
 * Gerencia cards mobile, lazy loading e interações touch
 */

// ===========================
// VARIÁVEIS GLOBAIS
// ===========================
let clientesMobileData = [];
let clientesMobileCarregados = 0;
let clientesMobilePorPagina = 10;
let filtrosAtivosMobile = 0;

// ===========================
// INICIALIZAÇÃO
// ===========================
document.addEventListener('DOMContentLoaded', function() {
    // ALTERADO: 991px para cobrir iPhones Pro Max e tablets pequenos
    if (window.innerWidth <= 991) {
        inicializarMobile();
    }

    // Listener para mudanças de orientação/resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth <= 991 && clientesMobileData.length === 0) {
                inicializarMobile();
            }
        }, 250);
    });
});

// ===========================
// INICIALIZAR MOBILE
// ===========================
function inicializarMobile() {
    console.log('[Mobile] Inicializando versão mobile...');

    // Converter dados da tabela para array de objetos
    converterTabelaParaCards();

    // Renderizar primeiros cards
    renderizarCardsMobile(0, clientesMobilePorPagina);

    // Inicializar bottom sheet de filtros
    inicializarBottomSheetFiltros();

    // Contar filtros ativos
    atualizarContadorFiltros();
}

// ===========================
// CONVERTER TABELA PARA CARDS
// ===========================
function converterTabelaParaCards() {
    console.log('[Mobile] Convertendo tabela HTML para cards...');

    clientesMobileData = [];

    // Pegar linhas diretamente do HTML da tabela (não do DataTable)
    const rows = document.querySelectorAll('#tabelaClientes tbody tr');

    if (rows.length === 0) {
        console.warn('[Mobile] Nenhuma linha encontrada na tabela');
        return;
    }

    rows.forEach(function(row) {
        const cells = row.querySelectorAll('td');

        if (cells.length < 8) {
            console.warn('[Mobile] Linha com células insuficientes, pulando...');
            return;
        }

        // Extrair dados de cada célula
        const cnpj = cells[0].textContent.trim();
        const nomeCompleto = extrairTextoCompleto(cells[1]);
        const nomeReduzido = extrairNomeReduzido(cells[1]);
        const uf = extrairUFDaCelula(cells[2]);
        const municipio = cells[3].textContent.trim();
        const vendedor = extrairVendedorDaCelula(cells[4]);
        const pedidos = parseInt(cells[6].textContent.trim()) || 0;
        const valorTexto = cells[7].textContent.trim();
        const valor = extrairValorNumerico(valorTexto);

        clientesMobileData.push({
            cnpj: cnpj,
            nome: {
                completo: nomeCompleto,
                reduzido: nomeReduzido
            },
            uf: uf,
            municipio: municipio,
            vendedor: vendedor,
            pedidos: pedidos,
            valor: valor,
            valorFormatado: valorTexto
        });
    });

    console.log(`[Mobile] ${clientesMobileData.length} clientes convertidos para cards`);
}

// ===========================
// FUNÇÕES AUXILIARES DE EXTRAÇÃO (HTML DIRETO)
// ===========================
function extrairTextoCompleto(celula) {
    // Procurar por elemento com title (razão social completa)
    const spanComTitle = celula.querySelector('span[title]');
    if (spanComTitle && spanComTitle.getAttribute('title')) {
        return spanComTitle.getAttribute('title');
    }
    return celula.textContent.trim().split('\n')[0].trim();
}

function extrairNomeReduzido(celula) {
    // Procurar pelo último badge-info (razão social reduzida)
    const badges = celula.querySelectorAll('.badge-info');
    if (badges.length > 0) {
        const ultimoBadge = badges[badges.length - 1];
        return ultimoBadge.textContent.trim();
    }
    return celula.textContent.trim().split('\n')[0].trim();
}

function extrairUFDaCelula(celula) {
    // Procurar por badge-secondary (UF)
    const badge = celula.querySelector('.badge-secondary');
    if (badge) {
        return badge.textContent.trim();
    }
    return celula.textContent.trim();
}

function extrairVendedorDaCelula(celula) {
    // Pegar primeira linha do texto (nome do vendedor)
    const texto = celula.textContent.trim();
    const linhas = texto.split('\n').map(l => l.trim()).filter(l => l);
    return linhas[0] || '-';
}

function extrairValorNumerico(texto) {
    // Remover R$, pontos de milhar e converter vírgula em ponto
    const valorLimpo = texto.replace('R$', '').replace(/\./g, '').replace(',', '.').trim();
    return parseFloat(valorLimpo) || 0;
}

// ===========================
// RENDERIZAR CARDS MOBILE
// ===========================
function renderizarCardsMobile(inicio, quantidade) {
    const container = document.getElementById('clientesListaMobile');

    if (!container) {
        console.warn('[Mobile] Container #clientesListaMobile não encontrado');
        return;
    }

    const fim = Math.min(inicio + quantidade, clientesMobileData.length);

    // Se é a primeira renderização, limpar container
    if (inicio === 0) {
        container.innerHTML = '';
    }

    // Se não há clientes, mostrar mensagem
    if (clientesMobileData.length === 0) {
        container.innerHTML = `
            <div class="clientes-mobile-empty">
                <i class="fas fa-inbox"></i>
                <p>Nenhum cliente encontrado com os filtros selecionados.</p>
            </div>
        `;
        // Ocultar botão carregar mais
        const btnCarregar = document.getElementById('btnCarregarMais');
        if (btnCarregar) btnCarregar.style.display = 'none';
        return;
    }

    // Renderizar cards
    for (let i = inicio; i < fim; i++) {
        const cliente = clientesMobileData[i];
        const card = criarCardCliente(cliente);
        container.insertAdjacentHTML('beforeend', card);
    }

    clientesMobileCarregados = fim;

    // Atualizar botão "Carregar Mais"
    atualizarBotaoCarregarMais();

    console.log(`[Mobile] Renderizados ${fim - inicio} cards (${inicio} a ${fim - 1})`);
}

// ===========================
// CRIAR CARD HTML
// ===========================
function criarCardCliente(cliente) {
    // Truncar nome se muito longo
    const nomeExibicao = cliente.nome.reduzido.length > 35
        ? cliente.nome.reduzido.substring(0, 32) + '...'
        : cliente.nome.reduzido;

    return `
        <div class="cliente-card-mobile" onclick="verPedidosMobile('${cliente.cnpj}', '${cliente.nome.reduzido.replace(/'/g, "\\'")}')">
            <div class="cliente-card-mobile-header">
                <div style="flex: 1;">
                    <div class="cliente-card-mobile-cnpj">${cliente.cnpj}</div>
                    <div class="cliente-card-mobile-nome" title="${cliente.nome.completo}">
                        ${nomeExibicao}
                    </div>
                </div>
            </div>

            <div class="cliente-card-mobile-body">
                <div class="cliente-card-mobile-row">
                    <span class="emoji">📍</span>
                    <span>${cliente.uf} • ${cliente.municipio || '-'}</span>
                </div>

                ${cliente.vendedor !== '-' ? `
                <div class="cliente-card-mobile-row">
                    <span class="emoji">👤</span>
                    <span>${cliente.vendedor}</span>
                </div>
                ` : ''}
            </div>

            <div class="cliente-card-mobile-footer">
                <div>
                    <div class="cliente-card-mobile-valor">${cliente.valorFormatado}</div>
                    <div style="font-size: 0.75rem; color: #8e8ea0; margin-top: 0.1rem;">
                        <span class="emoji" style="font-size: 0.85rem;">📦</span> ${cliente.pedidos} pedido${cliente.pedidos !== 1 ? 's' : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ===========================
// BOTÃO CARREGAR MAIS
// ===========================
function atualizarBotaoCarregarMais() {
    let btnCarregar = document.getElementById('btnCarregarMais');

    // Criar botão se não existir
    if (!btnCarregar) {
        const container = document.getElementById('clientesListaMobile');
        container.insertAdjacentHTML('afterend', `
            <button id="btnCarregarMais" onclick="carregarMaisClientes()">
                <i class="fas fa-chevron-down"></i> Carregar Mais (<span id="countRestantes">0</span> restantes)
            </button>
        `);
        btnCarregar = document.getElementById('btnCarregarMais');
    }

    const restantes = clientesMobileData.length - clientesMobileCarregados;

    if (restantes > 0) {
        btnCarregar.style.display = 'block';
        document.getElementById('countRestantes').textContent = restantes;
    } else {
        btnCarregar.style.display = 'none';
    }
}

function carregarMaisClientes() {
    const inicio = clientesMobileCarregados;
    renderizarCardsMobile(inicio, clientesMobilePorPagina);
}

// ===========================
// VER PEDIDOS (MOBILE)
// ===========================
function verPedidosMobile(cnpj, nomeCliente) {
    // Chamar função original do desktop
    verPedidos(cnpj, nomeCliente);
}

// ===========================
// BOTTOM SHEET DE FILTROS
// ===========================
function inicializarBottomSheetFiltros() {
    const btnFiltros = document.getElementById('filtrosMobileButton');
    const overlay = document.getElementById('bottomSheetOverlay');
    const bottomSheet = document.getElementById('bottomSheetFiltros');
    const btnFechar = document.getElementById('btnFecharFiltros');
    const btnLimpar = document.getElementById('btnLimparFiltrosMobile');
    const btnAplicar = document.getElementById('btnAplicarFiltrosMobile');

    if (!btnFiltros || !bottomSheet) {
        console.warn('[Mobile] Elementos de bottom sheet não encontrados');
        return;
    }

    // Abrir bottom sheet
    btnFiltros.addEventListener('click', function() {
        overlay.classList.add('show');
        bottomSheet.classList.add('show');
        document.body.style.overflow = 'hidden';
    });

    // Fechar bottom sheet
    const fecharSheet = () => {
        overlay.classList.remove('show');
        bottomSheet.classList.remove('show');
        document.body.style.overflow = '';
    };

    overlay.addEventListener('click', fecharSheet);
    btnFechar.addEventListener('click', fecharSheet);

    // Limpar filtros
    btnLimpar.addEventListener('click', function() {
        limparFiltrosMobile();
    });

    // Aplicar filtros
    btnAplicar.addEventListener('click', function() {
        aplicarFiltrosMobile();
        fecharSheet();
    });

    // Swipe down para fechar
    let touchStartY = 0;
    let touchEndY = 0;

    bottomSheet.addEventListener('touchstart', function(e) {
        touchStartY = e.changedTouches[0].screenY;
    }, {passive: true});

    bottomSheet.addEventListener('touchend', function(e) {
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
    }, {passive: true});

    function handleSwipe() {
        if (touchEndY - touchStartY > 100) {
            fecharSheet();
        }
    }
}

// ===========================
// LIMPAR FILTROS MOBILE
// ===========================
function limparFiltrosMobile() {
    document.getElementById('filtroMobileCnpj').value = '';
    document.getElementById('filtroMobileCliente').value = '';
    document.getElementById('filtroMobilePedido').value = '';
    document.getElementById('filtroMobileUF').value = '';

    atualizarContadorFiltros();
}

// ===========================
// APLICAR FILTROS MOBILE
// ===========================
function aplicarFiltrosMobile() {
    const cnpj = document.getElementById('filtroMobileCnpj').value.trim();
    const cliente = document.getElementById('filtroMobileCliente').value.trim();
    const pedido = document.getElementById('filtroMobilePedido').value.trim();
    const uf = document.getElementById('filtroMobileUF').value;

    // Construir URL com parâmetros
    const params = new URLSearchParams(window.location.search);

    // Manter posição e filtros de equipe/vendedor
    if (cnpj) params.set('cnpj_cpf', cnpj);
    else params.delete('cnpj_cpf');

    if (cliente) params.set('cliente', cliente);
    else params.delete('cliente');

    if (pedido) params.set('pedido', pedido);
    else params.delete('pedido');

    if (uf) params.set('uf', uf);
    else params.delete('uf');

    // Redirecionar com novos filtros
    window.location.search = params.toString();
}

// ===========================
// ATUALIZAR CONTADOR DE FILTROS
// ===========================
function atualizarContadorFiltros() {
    const params = new URLSearchParams(window.location.search);

    filtrosAtivosMobile = 0;

    if (params.get('cnpj_cpf')) filtrosAtivosMobile++;
    if (params.get('cliente')) filtrosAtivosMobile++;
    if (params.get('pedido')) filtrosAtivosMobile++;
    if (params.get('uf')) filtrosAtivosMobile++;

    // Atualizar badge no botão
    const badgeFiltros = document.getElementById('badgeFiltrosAtivos');
    if (badgeFiltros) {
        if (filtrosAtivosMobile > 0) {
            badgeFiltros.textContent = filtrosAtivosMobile;
            badgeFiltros.style.display = 'flex';
        } else {
            badgeFiltros.style.display = 'none';
        }
    }
}

// ===========================
// EXPORTAR EXCEL (MOBILE)
// ===========================
function exportarExcelMobile() {
    exportarExcel(); // Chama função desktop original
}

console.log('[Mobile] Script carregado com sucesso');
