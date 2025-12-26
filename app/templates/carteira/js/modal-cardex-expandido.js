/**
 * 📊 MODAL DE CARDEX EXPANDIDO
 * Exibe detalhes completos de saídas do produto por data
 */

class ModalCardexExpandido {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Modal Cardex Expandido inicializado');
        this.injectStyles();
    }

    /**
     * Injeta estilos CSS necessários
     */
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .pedidos-por-data .card {
                transition: all 0.3s ease;
                border-radius: 0.25rem;
            }
            
            .pedidos-por-data .card.border-3 {
                border-width: 3px !important;
            }
            
            .pedidos-por-data .card-header {
                font-size: 0.85rem;
                user-select: none;
            }
            
            .pedidos-por-data .card-header:hover {
                background-color: rgba(0,0,0,0.03);
            }
            
            .pedidos-por-data .table {
                font-size: 0.8rem;
            }
            
            .pedidos-por-data .badge {
                font-size: 0.7rem;
                padding: 0.2rem 0.4rem;
            }
            
            .pedidos-por-data .badge-sm {
                font-size: 0.65rem;
                padding: 0.15rem 0.3rem;
            }
            
            .dia-card[data-tem-ruptura="true"] {
                border-left: 3px solid var(--semantic-danger, #dc3545);
            }

            .dia-card[data-tem-ruptura="false"] {
                border-left: 3px solid var(--semantic-success, #28a745);
            }
            
            .dia-card .fa-chevron-down,
            .dia-card .fa-chevron-up {
                transition: transform 0.3s ease;
            }
            
            .dia-card .fa-chevron-up {
                transform: rotate(180deg);
            }
        `;
        document.head.appendChild(style);
    }

    async abrirCardexExpandido(codProduto, dataInicio = null) {
        console.log(`📊 Abrindo cardex expandido para produto ${codProduto}`);
        
        try {
            // Buscar dados detalhados do cardex com saídas
            const url = dataInicio 
                ? `/carteira/api/produto/${codProduto}/cardex-detalhado?data_inicio=${dataInicio}`
                : `/carteira/api/produto/${codProduto}/cardex-detalhado`;
                
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar cardex detalhado');
            }
            
            // Criar ID único para esta instância
            const modalId = `modal-cardex-expandido-${codProduto}-${Date.now()}`;
            
            // Adicionar à navegação se existe
            if (window.modalNav) {
                window.modalNav.pushModal(modalId, `Cardex Detalhado - ${codProduto}`, {
                    codProduto: codProduto,
                    dados: data,
                    modalId: modalId
                });
            }
            
            // Renderizar modal
            this.mostrarModalCardexExpandido(codProduto, data, modalId);
            
        } catch (error) {
            console.error(`❌ Erro ao carregar cardex detalhado:`, error);
            
            // Mostrar erro ao usuário
            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: 'Não foi possível carregar o cardex detalhado. Por favor, tente novamente.'
                });
            } else {
                alert('Erro ao carregar cardex detalhado: ' + error.message);
            }
        }
    }

    mostrarModalCardexExpandido(codProduto, data, modalId) {
        // Usar o modalId fornecido ou criar um novo
        if (!modalId) {
            modalId = `modal-cardex-expandido-${codProduto}-${Date.now()}`;
        }
        
        // Remover modal anterior do mesmo produto se houver
        const modaisExistentes = document.querySelectorAll(`[id^="modal-cardex-expandido-${codProduto}"]`);
        modaisExistentes.forEach(m => m.remove());

        // Criar modal
        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = this.renderizarModalCardexExpandido(codProduto, data);

        // Adicionar ao DOM
        document.body.appendChild(modal);

        // Configurar eventos
        this.configurarEventos(modal);

        // Mostrar modal usando Bootstrap
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Remover modal quando fechar
        modal.addEventListener('hidden.bs.modal', () => {
            // Notificar navegação ANTES de remover (se não for navegação)
            if (window.modalNav && !modal._skipNavigation) {
                window.modalNav.popModal();
            }
            // Remover modal do DOM
            setTimeout(() => {
                if (modal.parentNode) {
                    modal.remove();
                }
            }, 100);
        });
    }

    renderizarModalCardexExpandido(codProduto, data) {
        const estoqueAtual = data.estoque_atual || 0;
        const projecaoResumo = data.projecao_resumo || [];
        const pedidosPorData = data.pedidos_por_data || {};

        return `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <!-- Header -->
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-table me-2"></i>
                            Cardex Detalhado - ${codProduto}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <!-- Body -->
                    <div class="modal-body">
                        <!-- Resumo -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <div class="d-flex align-items-center">
                                    <h6 class="mb-0">Estoque Atual:
                                        <span class="badge bg-success fs-6">${this.formatarQuantidade(estoqueAtual)}</span>
                                    </h6>
                                </div>
                            </div>
                            <div class="col-md-6 text-end">
                                <button class="btn btn-sm btn-outline-secondary"
                                        onclick="cardexExpandido.toggleFiltroRuptura(this)"
                                        data-mostrando-todos="true">
                                    <i class="fas fa-exclamation-triangle me-1"></i>
                                    Apenas Rupturas
                                </button>
                                <button class="btn btn-sm btn-secondary ms-2"
                                        onclick="cardexExpandido.exportarDetalhado('${codProduto}')">
                                    <i class="fas fa-download me-1"></i>
                                    Exportar Excel
                                </button>
                            </div>
                        </div>

                        <!-- Pedidos por Data -->
                        <div class="pedidos-por-data">
                            <h6 class="mb-3">
                                <i class="fas fa-calendar-alt me-2"></i>
                                Pedidos Agrupados por Data de Expedição
                            </h6>
                            
                            <div id="cardex-dias-container">
                                ${this.renderizarPedidosPorData(pedidosPorData, projecaoResumo)}
                            </div>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-1"></i> Fechar
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renderizarPedidosPorData(pedidosPorData, projecaoResumo) {
        // Verificar se pedidosPorData existe e é um objeto
        if (!pedidosPorData || typeof pedidosPorData !== 'object') {
            return `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Erro ao processar dados dos pedidos.
                </div>
            `;
        }
        
        // Separar pedidos sem data dos com data
        const pedidosSemData = pedidosPorData['sem_data'] || [];
        const datasComPedidos = Object.keys(pedidosPorData).filter(d => d !== 'sem_data').sort();
        
        if (datasComPedidos.length === 0 && pedidosSemData.length === 0) {
            return `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Nenhum pedido encontrado para este produto.
                </div>
            `;
        }

        // Criar Map de projeção para acesso rápido
        const projecaoMap = new Map();
        if (Array.isArray(projecaoResumo)) {
            projecaoResumo.forEach(dia => {
                if (dia && dia.data) {
                    projecaoMap.set(dia.data, dia);
                }
            });
        }

        // Agrupar pedidos por data
        const grupos = [];
        
        // Debug temporário
        console.log('📊 Modal Cardex Expandido - Debug:', {
            totalDatasComPedidos: datasComPedidos.length,
            datas: datasComPedidos,
            pedidosSemData: pedidosSemData.length,
            pedidosPorData: pedidosPorData
        });
        
        // Processar pedidos com data
        datasComPedidos.forEach(data => {
            const pedidos = pedidosPorData[data];
            const projecao = projecaoMap.get(data) || {};
            
            // Calcular totais
            const totalQtd = pedidos.reduce((sum, p) => sum + p.qtd, 0);
            // Mapear campos corretos do backend (cardex_api.py linha 193-197)
            const estoqueInicial = projecao.saldo_inicial || 0;
            const estoqueFinal = projecao.saldo_final || 0;
            const producao = projecao.entrada || 0;  // 'entrada' é o campo de produção
            const saidas = projecao.saida || 0;  // 'saida' é o total de saídas
            
            grupos.push({
                data: data,
                pedidos: pedidos,
                totalQtd: totalQtd,
                estoqueInicial: estoqueInicial,
                estoqueFinal: estoqueFinal,
                producao: producao,
                saidas: saidas,
                temRuptura: estoqueFinal < 0
            });
        });
        
        // Adicionar pedidos sem data no final
        if (pedidosSemData.length > 0) {
            const totalQtdSemData = pedidosSemData.reduce((sum, p) => sum + p.qtd, 0);
            grupos.push({
                data: 'sem_data',
                pedidos: pedidosSemData,
                totalQtd: totalQtdSemData,
                estoqueInicial: 0,
                estoqueFinal: 0,
                producao: 0,
                temRuptura: false
            });
        }

        // Renderizar grupos
        return grupos.map((grupo, index) => {
            const temRuptura = grupo.temRuptura;
            const diaLabel = this.calcularDiaLabel(grupo.data);
            const headerClass = temRuptura ? 'bg-danger text-white' : 'bg-success text-white';
            const borderClass = temRuptura ? 'border-danger' : 'border-success';
            
            // Tratamento especial para pedidos sem data
            if (grupo.data === 'sem_data') {
                return `
                    <div class="card dia-card mb-2 border-warning border-3" 
                         data-tem-ruptura="false"
                         data-data="sem_data">
                        <div class="card-header bg-warning text-dark py-1 px-2" 
                             style="cursor: pointer;"
                             onclick="cardexExpandido.toggleCard('sem_data')">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>Sem Data</strong>
                                    <span class="badge bg-dark ms-1">Pendente</span>
                                </div>
                                <div class="text-end">
                                    <small>
                                        Total: ${this.formatarQuantidade(grupo.totalQtd)} |
                                        ${grupo.pedidos.length} pedidos
                                    </small>
                                    <i class="fas fa-chevron-down ms-2"></i>
                                </div>
                            </div>
                        </div>
                        <div class="collapse" id="collapse-semdata">
                            <div class="card-body p-2">
                                ${this.renderizarTabelaPedidos(grupo.pedidos)}
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Formato para pedidos com data
            return `
                <div class="card dia-card mb-2 ${borderClass} border-3" 
                     data-tem-ruptura="${temRuptura}"
                     data-data="${grupo.data}">
                    <div class="card-header ${headerClass} py-1 px-2" 
                         style="cursor: pointer;"
                         onclick="cardexExpandido.toggleCard('${grupo.data}')">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${this.formatarData(grupo.data).substring(0, 5)}</strong>
                                <span class="badge bg-${temRuptura ? 'dark' : 'light text-dark'} ms-1">${diaLabel}</span>
                            </div>
                            <div class="text-end">
                                <small>
                                    Est: ${this.formatarQuantidade(grupo.estoqueInicial)} | 
                                    Saí: ${this.formatarQuantidade(grupo.saidas || grupo.totalQtd)} | 
                                    Prod: ${this.formatarQuantidade(grupo.producao)} | 
                                    Final: ${this.formatarQuantidade(grupo.estoqueFinal)} |
                                    ${grupo.pedidos.length} peds
                                </small>
                                <i class="fas fa-chevron-down ms-2"></i>
                            </div>
                        </div>
                    </div>
                    <div class="collapse" id="collapse-${grupo.data.replace(/-/g, '')}">
                        <div class="card-body p-2">
                            ${this.renderizarTabelaPedidos(grupo.pedidos)}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderizarTabelaPedidos(pedidos) {
        return `
            <table class="table table-sm table-hover mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Pedido</th>
                        <th>Cliente</th>
                        <th>Cidade</th>
                        <th class="text-end">Qtd</th>
                        <th class="text-center">Status</th>
                        <th class="text-center">Ações</th>
                    </tr>
                </thead>
                <tbody>
                    ${pedidos.map(pedido => `
                        <tr>
                            <td class="fw-bold">${pedido.num_pedido}</td>
                            <td title="${pedido.cliente}">${this.truncarTexto(pedido.cliente, 25)}</td>
                            <td>${pedido.cidade}/${pedido.uf}</td>
                            <td class="text-end">${this.formatarQuantidade(pedido.qtd)}</td>
                            <td class="text-center">
                                ${pedido.tem_separacao 
                                    ? '<span class="badge bg-success">Separado</span>'
                                    : '<span class="badge bg-warning">Pendente</span>'
                                }
                            </td>
                            <td class="text-center">
                                <button class="btn btn-sm btn-outline-secondary"
                                        onclick="cardexExpandido.abrirPedidoDetalhes('${pedido.num_pedido}')"
                                        title="Ver detalhes do pedido">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    calcularDiaLabel(dataStr) {
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        const data = new Date(dataStr + 'T12:00:00');
        data.setHours(0, 0, 0, 0);
        
        const diffTime = data - hoje;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Hoje';
        if (diffDays === 1) return 'Amanhã';
        if (diffDays < 0) return `D${diffDays}`;
        return `D+${diffDays}`;
    }

    toggleCard(data) {
        const collapseId = `collapse-${data.replace(/-/g, '')}`;
        const collapseEl = document.getElementById(collapseId);
        
        if (collapseEl) {
            // Toggle usando Bootstrap
            const bsCollapse = new bootstrap.Collapse(collapseEl, { toggle: true });
            
            // Atualizar ícone
            const card = document.querySelector(`[data-data="${data}"]`);
            if (card) {
                const icon = card.querySelector('.fa-chevron-down, .fa-chevron-up');
                if (icon) {
                    if (collapseEl.classList.contains('show')) {
                        icon.className = 'fas fa-chevron-down ms-2';
                    } else {
                        icon.className = 'fas fa-chevron-up ms-2';
                    }
                }
            }
        }
    }

    abrirPedidoDetalhes(numPedido) {
        console.log(`📦 Abrindo detalhes do pedido ${numPedido}`);
        
        // Verificar se o script do modal de pedido detalhes está carregado
        if (!window.pedidoDetalhes) {
            // Carregar script dinamicamente se não estiver carregado
            const script = document.createElement('script');
            script.src = '/static/carteira/js/modal-pedido-detalhes.js';
            script.onload = () => {
                if (window.pedidoDetalhes) {
                    window.pedidoDetalhes.abrirPedidoDetalhes(numPedido);
                }
            };
            document.head.appendChild(script);
        } else {
            window.pedidoDetalhes.abrirPedidoDetalhes(numPedido);
        }
    }

    configurarEventos(modal) {
        // Configurar eventos específicos do modal se necessário
    }

    truncarTexto(texto, maxLength) {
        if (!texto) return '-';
        if (texto.length <= maxLength) return texto;
        return texto.substring(0, maxLength) + '...';
    }

    toggleFiltroRuptura(btn) {
        const mostrandoTodos = btn.dataset.mostrandoTodos === 'true';
        const container = document.getElementById('cardex-dias-container');
        
        if (!container) return;
        
        const cards = container.querySelectorAll('.dia-card');
        
        cards.forEach(card => {
            const temRuptura = card.dataset.temRuptura === 'true';
            
            if (mostrandoTodos && !temRuptura) {
                // Esconder dias sem ruptura
                card.style.display = 'none';
            } else {
                // Mostrar todos
                card.style.display = 'block';
            }
        });
        
        // Atualizar texto do botão
        if (mostrandoTodos) {
            btn.innerHTML = '<i class="fas fa-eye me-1"></i> Mostrar Todos';
            btn.dataset.mostrandoTodos = 'false';
        } else {
            btn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i> Apenas Rupturas';
            btn.dataset.mostrandoTodos = 'true';
        }
    }

    exportarDetalhado(codProduto) {
        console.log(`📊 Exportando cardex detalhado para produto ${codProduto}`);
        // Implementar exportação detalhada para Excel
        alert('Exportação detalhada em desenvolvimento');
    }

    // Utilitários
    formatarQuantidade(qtd) {
        if (!qtd && qtd !== 0) return '0';
        return parseFloat(qtd).toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    formatarData(dataStr) {
        const dataComHora = dataStr.includes('T') ? dataStr : dataStr + 'T12:00:00';
        const data = new Date(dataComHora);

        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit'
        });
    }
}

// Disponibilizar globalmente
window.cardexExpandido = new ModalCardexExpandido();