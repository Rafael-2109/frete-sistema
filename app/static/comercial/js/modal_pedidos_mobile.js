/**
 * MODAL DE PEDIDOS - MOBILE
 * Adaptações para exibição full-screen em mobile
 */

// ===========================
// RENDERIZAR PEDIDOS (MOBILE)
// ===========================
function renderizarPedidosMobile(data, page) {
    const contentDiv = document.getElementById('pedidosContent');

    if (data.total === 0) {
        contentDiv.innerHTML = `
            <div class="alert alert-info m-3">
                <i class="fas fa-info-circle"></i> Nenhum pedido encontrado para este cliente.
            </div>
        `;
        return;
    }

    let html = '<div class="pedidos-mobile-list">';

    // Renderizar cada pedido como card
    data.pedidos.forEach(function(pedido) {
        html += criarCardPedidoMobile(pedido);
    });

    html += '</div>';

    contentDiv.innerHTML = html;

    // Atualizar paginação
    $('#paginationInfo').html(`
        <span class="text-muted" style="font-size: 0.85rem;">
            ${((page - 1) * 20) + 1} a ${Math.min(page * 20, data.total)} de ${data.total}
        </span>
    `);

    atualizarPaginacao(data.page, data.total_pages);
}

// ===========================
// CRIAR CARD DE PEDIDO (MOBILE)
// ===========================
function criarCardPedidoMobile(pedido) {
    // Determinar cor e ícone do status
    let statusClass = '';
    let statusIcon = '';

    switch(pedido.status) {
        case 'Em Aberto':
            statusClass = 'badge-info';
            statusIcon = 'fa-clock';
            break;
        case 'Parcialmente Faturado':
            statusClass = 'badge-warning';
            statusIcon = 'fa-tasks';
            break;
        case 'Parcialmente Entregue':
            statusClass = 'badge-primary';
            statusIcon = 'fa-truck';
            break;
        case 'Entregue':
            statusClass = 'badge-success';
            statusIcon = 'fa-check-circle';
            break;
        default:
            statusClass = 'badge-secondary';
            statusIcon = 'fa-question-circle';
    }

    const pedidoId = pedido.num_pedido.replace(/[^a-zA-Z0-9]/g, '_');

    return `
        <div class="pedido-card-mobile" id="pedidoCard_${pedidoId}">
            <!-- Header do Card -->
            <div class="pedido-card-mobile-header">
                <div class="pedido-card-mobile-numero">
                    <span class="emoji">📦</span>
                    <strong>${pedido.num_pedido}</strong>
                </div>
                <span class="badge ${statusClass}">
                    <i class="fas ${statusIcon}"></i> ${pedido.status}
                </span>
            </div>

            <!-- Informações Principais -->
            <div class="pedido-card-mobile-body">
                ${pedido.pedido_cliente ? `
                <div class="pedido-info-row">
                    <span class="pedido-info-label">Pedido Cliente:</span>
                    <span class="pedido-info-value">${pedido.pedido_cliente}</span>
                </div>
                ` : ''}

                <div class="pedido-info-row">
                    <span class="pedido-info-label">Data:</span>
                    <span class="pedido-info-value">${pedido.data_pedido || '-'}</span>
                </div>

                ${pedido.incoterm && pedido.incoterm !== '-' ? `
                <div class="pedido-info-row">
                    <span class="pedido-info-label">Incoterm:</span>
                    <span class="pedido-info-value">${pedido.incoterm}</span>
                </div>
                ` : ''}
            </div>

            <!-- Valores -->
            <div class="pedido-card-mobile-valores">
                <div class="pedido-valor-item">
                    <small>Total Pedido</small>
                    <strong class="valor-total">R$ ${formatarMoeda(pedido.valor_total_pedido)}</strong>
                </div>
                ${pedido.valor_total_faturado > 0 ? `
                <div class="pedido-valor-item">
                    <small>Faturado</small>
                    <strong class="valor-faturado">R$ ${formatarMoeda(pedido.valor_total_faturado)}</strong>
                </div>
                ` : ''}
                ${pedido.valor_entregue > 0 ? `
                <div class="pedido-valor-item">
                    <small>Entregue</small>
                    <strong class="valor-entregue">R$ ${formatarMoeda(pedido.valor_entregue)}</strong>
                </div>
                ` : ''}
                ${pedido.saldo_carteira > 0 ? `
                <div class="pedido-valor-item">
                    <small>Saldo</small>
                    <strong class="valor-saldo">R$ ${formatarMoeda(pedido.saldo_carteira)}</strong>
                </div>
                ` : ''}
            </div>

            <!-- Botão Ver Documentos -->
            <button class="pedido-card-mobile-btn-docs"
                    onclick="toggleDocumentosMobile('${pedido.num_pedido}', '${currentCnpj}', '${pedidoId}')">
                <i class="fas fa-chevron-down" id="iconDocs_${pedidoId}"></i>
                Ver Documentos
            </button>

            <!-- Container de Documentos (oculto inicialmente) -->
            <div class="pedido-card-mobile-docs" id="docs_${pedidoId}" style="display: none;">
                <div class="text-center p-3 text-secondary-color">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span class="ms-2">Carregando documentos...</span>
                </div>
            </div>
        </div>
    `;
}

// ===========================
// TOGGLE DOCUMENTOS (MOBILE)
// ===========================
let documentosCarregadosMobile = {};

function toggleDocumentosMobile(numPedido, cnpj, pedidoId) {
    const docsDiv = document.getElementById(`docs_${pedidoId}`);
    const icon = document.getElementById(`iconDocs_${pedidoId}`);

    if (docsDiv.style.display === 'none') {
        // Expandir
        docsDiv.style.display = 'block';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');

        // Carregar documentos se ainda não foram carregados
        if (!documentosCarregadosMobile[numPedido]) {
            carregarDocumentosPedidoMobile(numPedido, cnpj, pedidoId);
        }
    } else {
        // Colapsar
        docsDiv.style.display = 'none';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

// ===========================
// CARREGAR DOCUMENTOS (MOBILE)
// ===========================
function carregarDocumentosPedidoMobile(numPedido, cnpj, pedidoId) {
    const docsDiv = document.getElementById(`docs_${pedidoId}`);
    const cnpjDecoded = decodeURIComponent(cnpj);

    $.ajax({
        url: `/comercial/api/pedido/${encodeURIComponent(numPedido)}/documentos`,
        data: { cnpj: cnpjDecoded },
        success: function(data) {
            documentosCarregadosMobile[numPedido] = true;
            renderizarDocumentosMobile(data, docsDiv);
        },
        error: function() {
            docsDiv.innerHTML = `
                <div class="alert alert-danger m-2">
                    <i class="fas fa-exclamation-circle"></i> Erro ao carregar documentos
                </div>
            `;
        }
    });
}

// ===========================
// RENDERIZAR DOCUMENTOS (MOBILE)
// ===========================
function renderizarDocumentosMobile(data, docsDiv) {
    if (data.documentos.length === 0) {
        docsDiv.innerHTML = `
            <div class="alert m-2 text-secondary-color">
                <i class="fas fa-info-circle"></i> Nenhum documento encontrado
            </div>
        `;
        return;
    }

    let html = '<div class="documentos-mobile-list">';

    data.documentos.forEach(function(doc, index) {
        let badgeClass = '';
        let badgeIcon = '';
        let tipoApi = '';
        let identificador = '';

        switch(doc.tipo) {
            case 'NF':
                badgeClass = 'badge-success';
                badgeIcon = 'fa-file-invoice';
                tipoApi = 'NF';
                identificador = doc.numero_nf;
                break;
            case 'Separação':
                badgeClass = 'badge-warning';
                badgeIcon = 'fa-box-open';
                tipoApi = 'Separacao';
                identificador = doc.separacao_lote_id;
                break;
            case 'Saldo':
                badgeClass = 'badge-info';
                badgeIcon = 'fa-calculator';
                tipoApi = 'Saldo';
                identificador = doc.num_pedido || data.num_pedido;
                break;
        }

        const docId = `${tipoApi}_${identificador}_${index}`.replace(/[^a-zA-Z0-9_]/g, '_');

        html += `
            <div class="documento-card-mobile">
                <!-- Header -->
                <div class="documento-card-mobile-header">
                    <span class="badge ${badgeClass}">
                        <i class="fas ${badgeIcon}"></i> ${doc.tipo}
                    </span>
                    ${doc.numero_nf ? `<span class="documento-nf">NF ${doc.numero_nf}</span>` : ''}
                </div>

                <!-- Informações -->
                <div class="documento-card-mobile-body">
                    ${doc.valor && doc.valor !== '-' ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Valor:</span>
                        <strong class="documento-info-valor">R$ ${formatarMoeda(doc.valor)}</strong>
                    </div>
                    ` : ''}

                    ${doc.data_faturamento ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Faturamento:</span>
                        <span>${doc.data_faturamento}</span>
                    </div>
                    ` : ''}

                    ${doc.data_embarque ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Embarque:</span>
                        <span>${doc.data_embarque}</span>
                    </div>
                    ` : ''}

                    ${doc.transportadora && doc.transportadora !== '-' ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Transportadora:</span>
                        <span>${doc.transportadora}</span>
                    </div>
                    ` : ''}

                    ${data.cliente_precisa_agendamento && doc.data_agendamento ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Agendamento:</span>
                        <span>${doc.data_agendamento}</span>
                    </div>
                    ` : ''}

                    ${data.cliente_precisa_agendamento && doc.protocolo_agendamento ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Protocolo:</span>
                        <span>${doc.protocolo_agendamento}</span>
                    </div>
                    ` : ''}

                    ${!data.cliente_precisa_agendamento && doc.data_entrega_prevista ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Entrega Prevista:</span>
                        <span>${doc.data_entrega_prevista}</span>
                    </div>
                    ` : ''}

                    ${doc.data_entrega_realizada ? `
                    <div class="documento-info-row">
                        <span class="documento-info-label">Entrega Realizada:</span>
                        <span>${doc.data_entrega_realizada}</span>
                    </div>
                    ` : ''}
                </div>

                <!-- Botão Ver Produtos -->
                <button class="documento-btn-produtos"
                        onclick="toggleProdutosMobile('${docId}', '${tipoApi}', '${identificador}', '${doc.num_pedido || ''}')">
                    <i class="fas fa-chevron-down" id="iconProds_${docId}"></i>
                    Ver Produtos
                </button>

                <!-- Container de Produtos -->
                <div class="documento-produtos" id="prods_${docId}" style="display: none;">
                    <div class="text-center p-2 text-secondary-color" style="font-size: 0.85rem;">
                        <i class="fas fa-spinner fa-spin"></i> Carregando produtos...
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';

    docsDiv.innerHTML = html;
}

// ===========================
// TOGGLE PRODUTOS (MOBILE)
// ===========================
let produtosCarregadosMobile = {};

function toggleProdutosMobile(docId, tipo, identificador, numPedido) {
    const prodsDiv = document.getElementById(`prods_${docId}`);
    const icon = document.getElementById(`iconProds_${docId}`);

    if (prodsDiv.style.display === 'none') {
        // Expandir
        prodsDiv.style.display = 'block';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');

        // Carregar produtos se ainda não foram carregados
        const cacheKey = `${tipo}_${identificador}`;
        if (!produtosCarregadosMobile[cacheKey]) {
            carregarProdutosMobile(docId, tipo, identificador, numPedido);
        }
    } else {
        // Colapsar
        prodsDiv.style.display = 'none';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

// ===========================
// CARREGAR PRODUTOS (MOBILE)
// ===========================
function carregarProdutosMobile(docId, tipo, identificador, numPedido) {
    const prodsDiv = document.getElementById(`prods_${docId}`);

    let url = `/comercial/api/documento/${tipo}/${encodeURIComponent(identificador)}/produtos`;
    if (numPedido) {
        url += `?num_pedido=${encodeURIComponent(numPedido)}`;
    }

    $.ajax({
        url: url,
        type: 'GET',
        success: function(data) {
            const cacheKey = `${tipo}_${identificador}`;
            produtosCarregadosMobile[cacheKey] = data;
            renderizarProdutosMobile(data, prodsDiv);
        },
        error: function(xhr, status, error) {
            prodsDiv.innerHTML = `
                <div class="alert alert-danger m-2" style="font-size: 0.85rem;">
                    <i class="fas fa-exclamation-triangle"></i> Erro ao carregar produtos
                </div>
            `;
        }
    });
}

// ===========================
// RENDERIZAR PRODUTOS (MOBILE)
// ===========================
function renderizarProdutosMobile(data, prodsDiv) {
    if (!data.produtos || data.produtos.length === 0) {
        prodsDiv.innerHTML = `
            <div class="alert m-2 text-secondary-color" style="font-size: 0.85rem;">
                <i class="fas fa-info-circle"></i> Nenhum produto encontrado
            </div>
        `;
        return;
    }

    let html = '<div class="produtos-mobile-list">';

    data.produtos.forEach(function(prod) {
        html += `
            <div class="produto-card-mobile">
                <div class="produto-codigo">${prod.codigo}</div>
                <div class="produto-nome">${prod.produto}</div>
                <div class="produto-detalhes">
                    <span>Qtd: <strong>${formatarNumero(prod.quantidade, 0)}</strong></span>
                    <span>Preço: <strong>R$ ${formatarMoeda(prod.preco)}</strong></span>
                </div>
                <div class="produto-valor">
                    Total: <strong>R$ ${formatarMoeda(prod.valor)}</strong>
                </div>
            </div>
        `;
    });

    html += '</div>';

    prodsDiv.innerHTML = html;
}

// ===========================
// DETECTAR MOBILE E ADAPTAR
// ===========================
function adaptarModalParaMobile() {
    if (window.innerWidth <= 767) {
        // Usar renderização mobile
        const originalRenderizar = renderizarDocumentos;

        // Override função de renderização se em mobile
        window.renderizarDocumentosMobileOverride = true;
    }
}

// Inicializar ao carregar
document.addEventListener('DOMContentLoaded', function() {
    adaptarModalParaMobile();

    // Listener para mudanças de orientação
    window.addEventListener('resize', function() {
        adaptarModalParaMobile();
    });
});

console.log('[Mobile] Script modal_pedidos_mobile.js carregado');
