/**
 * 📦 MODAL DE DETALHES DO PEDIDO
 * Exibe informações completas do pedido similar ao workspace de montagem
 */

class ModalPedidoDetalhes {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Modal Pedido Detalhes inicializado');
    }

    async abrirPedidoDetalhes(numPedido) {
        console.log(`📦 Abrindo detalhes do pedido ${numPedido}`);

        try {
            // Buscar dados completos do pedido usando a rota específica para o modal
            const response = await fetch(`/carteira/api/pedido/${numPedido}/detalhes-completo`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar detalhes do pedido');
            }

            // Criar ID único para esta instância
            const modalId = `modal-pedido-detalhes-${numPedido}-${Date.now()}`;

            // Adicionar à navegação se existe
            if (window.modalNav) {
                window.modalNav.pushModal(modalId, `Pedido ${numPedido}`, {
                    numPedido: numPedido,
                    dados: data,
                    modalId: modalId
                });
            }

            // Renderizar modal
            this.mostrarModalPedido(numPedido, data);

        } catch (error) {
            console.error(`❌ Erro ao carregar detalhes do pedido:`, error);

            // Mostrar erro ao usuário
            if (window.Swal) {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: 'Não foi possível carregar os detalhes do pedido. Por favor, tente novamente.'
                });
            } else {
                alert('Erro ao carregar detalhes do pedido: ' + error.message);
            }
        }
    }

    mostrarModalPedido(numPedido, data) {
        // Criar ID único para esta instância do modal
        const modalId = `modal-pedido-detalhes-${numPedido}-${Date.now()}`;

        // Remover modal anterior do mesmo pedido se houver
        const modaisExistentes = document.querySelectorAll(`[id^="modal-pedido-detalhes-${numPedido}"]`);
        modaisExistentes.forEach(m => m.remove());

        // Criar modal
        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = this.renderizarModalPedido(numPedido, data);

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

    renderizarModalPedido(numPedido, data) {
        const pedido = data.pedido || {};
        const itens = data.itens || [];
        const separacoes = data.separacoes || [];

        return `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <!-- Header -->
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-box me-2"></i>
                            Detalhes do Pedido ${numPedido}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <!-- Body -->
                    <div class="modal-body">
                        <!-- Informações do Cliente e Pedido -->
                        <div class="card mb-3">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-user me-2"></i>Informações do Cliente
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <strong>Cliente:</strong><br>
                                        ${pedido.raz_social_red || '-'}<br>
                                        <small class="text-muted">CNPJ: ${pedido.cnpj_cpf || '-'}</small>
                                    </div>
                                    <div class="col-md-4">
                                        <strong>Localização:</strong><br>
                                        ${pedido.nome_cidade || '-'} / ${pedido.cod_uf || '-'}<br>
                                        <small class="text-muted">
                                            Rota: ${pedido.rota || '-'} | Sub-rota: ${pedido.sub_rota || '-'}
                                        </small>
                                    </div>
                                    <div class="col-md-4">
                                        <strong>Vendedor:</strong><br>
                                        ${pedido.vendedor || '-'}<br>
                                        <small class="text-muted">Equipe: ${pedido.equipe_vendas || '-'}</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Informações de Expedição e Agendamento -->
                        <div class="card mb-3">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-calendar me-2"></i>Expedição e Agendamento
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3">
                                        <strong>Data Pedido:</strong><br>
                                        ${this.formatarData(pedido.data_pedido)}
                                    </div>
                                    <div class="col-md-3">
                                        <strong>Expedição:</strong><br>
                                        <span class="badge bg-secondary">
                                            ${this.formatarData(pedido.expedicao_separacao || pedido.expedicao)}
                                        </span>
                                    </div>
                                    <div class="col-md-3">
                                        <strong>Agendamento:</strong><br>
                                        ${pedido.agendamento_separacao || pedido.agendamento ? `
                                            <span class="badge ${pedido.agendamento_confirmado ? 'bg-success' : 'bg-warning'}">
                                                ${this.formatarData(pedido.agendamento_separacao || pedido.agendamento)}
                                                ${pedido.hora_agendamento ? ` ${pedido.hora_agendamento}` : ''}
                                            </span>
                                        ` : '<span class="text-muted">Não agendado</span>'}
                                    </div>
                                    <div class="col-md-3">
                                        <strong>Protocolo:</strong><br>
                                        ${pedido.protocolo_separacao || pedido.protocolo || '<span class="text-muted">-</span>'}
                                    </div>
                                </div>
                                ${pedido.observ_ped_1 ? `
                                    <div class="row mt-3">
                                        <div class="col-12">
                                            <strong>Observações:</strong><br>
                                            <div class="alert alert-warning mb-0">
                                                <i class="fas fa-info-circle me-2"></i>
                                                ${pedido.observ_ped_1}
                                            </div>
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        </div>

                        <!-- Totais do Pedido -->
                        <div class="card mb-3">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-calculator me-2"></i>Resumo do Pedido
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row text-center">
                                    <div class="col-md-3">
                                        <div class="stat-box">
                                            <strong class="text-muted">Valor Total</strong><br>
                                            <span class="h4">
                                                R$ ${this.formatarMoeda(pedido.valor_total || 0)}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="stat-box">
                                            <strong class="text-muted">Peso Total</strong><br>
                                            <span class="h4">
                                                ${this.formatarNumero(pedido.peso_total || 0)} kg
                                            </span>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="stat-box">
                                            <strong class="text-muted">Pallets</strong><br>
                                            <span class="h4">
                                                ${this.formatarNumero(pedido.pallet_total || 0, 2)}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="stat-box">
                                            <strong class="text-muted">Total Itens</strong><br>
                                            <span class="h4">
                                                ${pedido.total_itens || 0}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Itens do Pedido -->
                        <div class="card mb-3">
                            <div class="card-header bg-light d-flex justify-content-between align-items-center">
                                <h6 class="mb-0">
                                    <i class="fas fa-list me-2"></i>Itens do Pedido
                                </h6>
                                <button class="btn btn-sm btn-outline-secondary" onclick="pedidoDetalhes.analisarDisponibilidade('${numPedido}')">
                                    <i class="fas fa-chart-line me-1"></i>Analisar Disponibilidade
                                </button>
                            </div>
                            <div class="card-body p-0">
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped mb-0">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>Código</th>
                                                <th>Produto</th>
                                                <th class="text-end">Qtd Original</th>
                                                <th class="text-end">Qtd Saldo</th>
                                                <th class="text-end">Preço Unit.</th>
                                                <th class="text-end">Valor Total</th>
                                                <th class="text-center">Estoque</th>
                                                <th class="text-center">Cardex</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${this.renderizarItens(itens)}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <!-- Separações -->
                        ${separacoes.length > 0 ? `
                            <div class="card">
                                <div class="card-header bg-light">
                                    <h6 class="mb-0">
                                        <i class="fas fa-truck me-2"></i>Separações Realizadas
                                    </h6>
                                </div>
                                <div class="card-body">
                                    ${this.renderizarSeparacoes(separacoes)}
                                </div>
                            </div>
                        ` : ''}
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

    renderizarItens(itens) {
        if (!itens || itens.length === 0) {
            return `
                <tr>
                    <td colspan="8" class="text-center text-muted py-3">
                        Nenhum item encontrado
                    </td>
                </tr>
            `;
        }

        return itens.map(item => {
            const valorTotal = (item.qtd_saldo_produto_pedido || 0) * (item.preco_produto_pedido || 0);
            const temRuptura = item.qtd_saldo_produto_pedido > (item.estoque || 0);

            return `
                <tr class="${temRuptura ? 'table-warning' : ''}">
                    <td>
                        ${item.cod_produto}
                        <button class="btn btn-sm btn-link p-0 ms-2" 
                                onclick="pedidoDetalhes.abrirCardex('${item.cod_produto}')"
                                title="Ver Cardex">
                            <i class="fas fa-chart-line"></i>
                        </button>
                    </td>
                    <td>${item.nome_produto || '-'}</td>
                    <td class="text-end">${this.formatarNumero(item.qtd_produto_pedido || 0)}</td>
                    <td class="text-end">
                        <strong>${this.formatarNumero(item.qtd_saldo_produto_pedido || 0)}</strong>
                    </td>
                    <td class="text-end">R$ ${this.formatarMoeda(item.preco_produto_pedido || 0)}</td>
                    <td class="text-end">
                        <strong>R$ ${this.formatarMoeda(valorTotal)}</strong>
                    </td>
                    <td class="text-center">
                        ${temRuptura ?
                    `<span class="badge bg-danger">
                                <i class="fas fa-exclamation-triangle"></i> Ruptura
                            </span>` :
                    `<span class="badge bg-success">
                                <i class="fas fa-check"></i> OK
                            </span>`
                }
                    </td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-outline-secondary"
                                onclick="pedidoDetalhes.abrirCardex('${item.cod_produto}')"
                                title="Ver Cardex">
                            <i class="fas fa-chart-line"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    renderizarSeparacoes(separacoes) {
        if (!separacoes || separacoes.length === 0) {
            return '<p class="text-muted p-3">Nenhuma separação realizada</p>';
        }

        return separacoes.map(sep => `
            <div class="card mb-3">
                <div class="card-header bg-light d-flex justify-content-between align-items-center">
                    <div>
                        <strong>Lote: ${sep.separacao_lote_id}</strong>
                        <span class="badge bg-secondary ms-2">
                            ${sep.tipo_envio}
                        </span>
                        <span class="badge bg-${this.getStatusColor(sep.status)} ms-1">
                            ${sep.status || 'ABERTO'}
                        </span>
                    </div>
                    <div>
                        ${sep.expedicao ? `
                            <span class="badge bg-secondary me-2">
                                <i class="fas fa-calendar-alt me-1"></i>
                                Exp: ${this.formatarData(sep.expedicao)}
                            </span>
                        ` : ''}
                        ${sep.agendamento ? `
                            <span class="badge bg-secondary me-2">
                                <i class="fas fa-clock me-1"></i>
                                Agenda: ${this.formatarData(sep.agendamento)}
                            </span>
                        ` : ''}
                        ${sep.protocolo ? `
                            <span class="badge bg-warning text-dark">
                                <i class="fas fa-tag me-1"></i>
                                ${sep.protocolo}
                            </span>
                        ` : ''}
                    </div>
                </div>
                <div class="card-body p-0">
                    <table class="table table-sm table-hover mb-0">
                        <thead class="table-secondary">
                            <tr>
                                <th>Código</th>
                                <th>Produto</th>
                                <th class="text-end">Qtd</th>
                                <th class="text-end">Peso</th>
                                <th class="text-end">Pallet</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sep.itens && sep.itens.length > 0 ? sep.itens.map(item => `
                                <tr>
                                    <td>${item.cod_produto}</td>
                                    <td>${item.nome_produto || '-'}</td>
                                    <td class="text-end">${this.formatarNumero(item.qtd)}</td>
                                    <td class="text-end">${this.formatarNumero(item.peso, 2)} kg</td>
                                    <td class="text-end">${this.formatarNumero(item.pallet, 2)}</td>
                                </tr>
                            `).join('') : `
                                <tr>
                                    <td colspan="5" class="text-center text-muted">
                                        Nenhum item na separação
                                    </td>
                                </tr>
                            `}
                        </tbody>
                        <tfoot class="table-light">
                            <tr>
                                <td colspan="2"><strong>Totais:</strong></td>
                                <td class="text-end">-</td>
                                <td class="text-end"><strong>${this.formatarNumero(sep.peso || 0, 2)} kg</strong></td>
                                <td class="text-end"><strong>${this.formatarNumero(sep.pallet || 0, 2)}</strong></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                <div class="card-footer text-muted small">
                    Criado em: ${this.formatarData(sep.criado_em)} | 
                    Valor Total: R$ ${this.formatarMoeda(sep.valor_saldo || 0)}
                </div>
            </div>
        `).join('');
    }

    getStatusColor(status) {
        const colors = {
            'ABERTO': 'secondary',
            'COTADO': 'info',
            'EMBARCADO': 'warning',
            'FATURADO': 'success',
            'CANCELADO': 'danger'
        };
        return colors[status] || 'secondary';
    }

    configurarEventos(modal) {
        // Configurar eventos específicos do modal se necessário
    }

    // Métodos de ação
    async analisarDisponibilidade(numPedido) {
        if (window.rupturaManager) {
            // Fechar este modal
            const modal = document.getElementById('modal-pedido-detalhes');
            if (modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            }

            // Abrir análise de ruptura
            const btn = document.querySelector(`[data-pedido="${numPedido}"]`);
            if (btn) {
                window.rupturaManager.analisarRuptura(numPedido, btn);
            } else {
                // Se não encontrar o botão, chamar diretamente
                const response = await fetch(`/carteira/api/ruptura/sem-cache/analisar-pedido/${numPedido}`);
                const data = await response.json();
                if (data.success) {
                    window.rupturaManager.mostrarModalRuptura(data);
                }
            }
        }
    }

    abrirCardex(codProduto) {
        // Criar Map com dados dos produtos se disponível
        const dadosProdutos = new Map();

        // Integração com navegação
        if (window.modalNav) {
            window.modalNav.pushModal('modalCardex', `Cardex - ${codProduto}`, {
                codProduto: codProduto,
                dadosProdutos: dadosProdutos
            });
        }

        if (window.modalCardex) {
            window.modalCardex.abrirCardex(codProduto, dadosProdutos);
        } else {
            // Carregar script se não estiver carregado
            const script = document.createElement('script');
            script.src = '/static/carteira/js/modal-cardex.js';
            script.onload = () => {
                if (window.modalCardex) {
                    window.modalCardex.abrirCardex(codProduto, dadosProdutos);
                }
            };
            document.head.appendChild(script);
        }
    }

    editarPedido(numPedido) {
        console.log(`Editando pedido ${numPedido}`);
        alert('Função de edição em desenvolvimento');
    }

    criarSeparacao(numPedido) {
        console.log(`Criando separação para pedido ${numPedido}`);
        if (window.separacaoManager) {
            // Fechar modal e abrir workspace de separação
            const modal = document.getElementById('modal-pedido-detalhes');
            if (modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            }

            // Simular clique no botão de separação
            const btn = document.querySelector(`[data-pedido="${numPedido}"] .btn-separacao`);
            if (btn) {
                btn.click();
            }
        }
    }

    editarItem(itemId) {
        console.log(`Editando item ${itemId}`);
        alert('Função de edição de item em desenvolvimento');
    }

    cancelarItem(itemId) {
        console.log(`Cancelando item ${itemId}`);
        if (confirm('Tem certeza que deseja cancelar este item?')) {
            alert('Função de cancelamento em desenvolvimento');
        }
    }

    verSeparacao(separacaoLoteId) {
        console.log(`Visualizando separação ${separacaoLoteId}`);
        alert('Função de visualização de separação em desenvolvimento');
    }


    // Utilitários
    formatarData(dataStr) {
        if (!dataStr) return '-';
        const dataComHora = dataStr.includes('T') ? dataStr : dataStr + 'T12:00:00';
        const data = new Date(dataComHora);

        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }

    formatarMoeda(valor) {
        return window.Formatters.moeda(valor);
    }

    formatarNumero(valor, decimais = 0) {
        return window.Formatters.numero(valor, decimais);
    }
}

// Disponibilizar globalmente
window.pedidoDetalhes = new ModalPedidoDetalhes();