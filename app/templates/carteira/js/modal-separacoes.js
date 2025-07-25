/**
 * 🎯 MODAL DE SEPARAÇÕES
 * Gerencia o modal de visualização de separações com paginação e totalizadores
 */

class ModalSeparacoes {
    constructor() {
        this.modalElement = null;
        this.modal = null;
        this.separacoes = [];
        this.paginaAtual = 1;
        this.separacoesPorPagina = 5;
        this.init();
    }

    init() {
        this.modalElement = document.getElementById('modalSeparacoes');
        if (this.modalElement) {
            this.modal = new bootstrap.Modal(this.modalElement);
        }
        console.log('✅ Modal de Separações inicializado');
    }

    async abrir(numPedido) {
        console.log(`📦 Abrindo modal de separações para pedido ${numPedido}`);
        
        // Atualizar número do pedido no título
        document.getElementById('modal-pedido-numero').textContent = numPedido;
        
        // Mostrar loading
        document.getElementById('modal-separacoes-loading').style.display = 'block';
        document.getElementById('modal-separacoes-content').style.display = 'none';
        
        // Abrir modal
        this.modal.show();
        
        try {
            // Carregar separações
            await this.carregarSeparacoes(numPedido);
        } catch (error) {
            console.error('❌ Erro ao carregar separações:', error);
            this.mostrarErro('Erro ao carregar separações. Tente novamente.');
        }
    }

    async carregarSeparacoes(numPedido) {
        try {
            const response = await fetch(`/carteira/api/pedido/${numPedido}/separacoes-completas`);
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar separações');
            }
            
            this.separacoes = data.separacoes || [];
            this.paginaAtual = 1;
            
            // Ocultar loading e mostrar conteúdo
            document.getElementById('modal-separacoes-loading').style.display = 'none';
            document.getElementById('modal-separacoes-content').style.display = 'block';
            
            // Renderizar separações
            this.renderizarSeparacoes();
            
        } catch (error) {
            throw error;
        }
    }

    renderizarSeparacoes() {
        const container = document.getElementById('modal-separacoes-content');
        
        if (this.separacoes.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle me-2"></i>
                    Nenhuma separação encontrada para este pedido.
                </div>
            `;
            return;
        }

        // Calcular totais gerais
        const totaisGerais = this.calcularTotaisGerais();
        
        // Calcular separações da página atual
        const inicio = (this.paginaAtual - 1) * this.separacoesPorPagina;
        const fim = inicio + this.separacoesPorPagina;
        const separacoesPagina = this.separacoes.slice(inicio, fim);
        
        let html = `
            <!-- Totalizadores Gerais -->
            <div class="card mb-3 border-primary">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-calculator me-2"></i>
                        Totais de Todas as Separações (${this.separacoes.length} separações)
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-md-4">
                            <h5 class="text-success">${this.formatarMoeda(totaisGerais.valor)}</h5>
                            <small class="text-muted">Valor Total</small>
                        </div>
                        <div class="col-md-4">
                            <h5 class="text-info">${this.formatarPeso(totaisGerais.peso)}</h5>
                            <small class="text-muted">Peso Total</small>
                        </div>
                        <div class="col-md-4">
                            <h5 class="text-warning">${this.formatarPallet(totaisGerais.pallet)}</h5>
                            <small class="text-muted">Pallets Total</small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Paginação Superior -->
            ${this.renderizarPaginacao()}

            <!-- Separações da Página -->
            <div class="separacoes-lista">
        `;

        // Renderizar cada separação
        separacoesPagina.forEach((separacao, index) => {
            html += this.renderizarSeparacao(separacao, inicio + index + 1);
        });

        html += `
            </div>

            <!-- Paginação Inferior -->
            ${this.renderizarPaginacao()}
        `;

        container.innerHTML = html;
    }

    renderizarSeparacao(separacao, numero) {
        const statusClass = this.getStatusClass(separacao.status);
        const statusBadge = this.getStatusBadge(separacao.status);
        
        let html = `
            <div class="card mb-3 border-${statusClass}">
                <div class="card-header bg-${statusClass} bg-opacity-10">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-box me-2"></i>
                            Separação #${numero} - ${separacao.separacao_lote_id}
                        </h6>
                        ${statusBadge}
                    </div>
                </div>
                <div class="card-body">
                    <!-- Informações Gerais -->
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <strong>Data Expedição:</strong><br>
                            ${this.formatarData(separacao.expedicao)}
                        </div>
                        <div class="col-md-3">
                            <strong>Agendamento:</strong><br>
                            ${separacao.agendamento ? this.formatarData(separacao.agendamento) : '-'}
                        </div>
                        <div class="col-md-3">
                            <strong>Protocolo:</strong><br>
                            ${separacao.protocolo || '-'}
                        </div>
                        <div class="col-md-3">
                            <strong>Status Calculado:</strong><br>
                            ${statusBadge}
                        </div>
                    </div>
        `;

        // Se status for COTADO, mostrar informações do embarque
        if (separacao.status === 'COTADO' && separacao.embarque) {
            html += `
                    <div class="alert alert-info mb-3">
                        <h6 class="alert-heading">
                            <i class="fas fa-truck me-2"></i>
                            Informações do Embarque
                        </h6>
                        <div class="row">
                            <div class="col-md-4">
                                <strong>Número:</strong> ${separacao.embarque.numero || '-'}
                            </div>
                            <div class="col-md-4">
                                <strong>Transportadora:</strong> ${separacao.embarque.transportadora || '-'}
                            </div>
                            <div class="col-md-4">
                                <strong>Previsão:</strong> ${separacao.embarque.data_prevista_embarque ? this.formatarData(separacao.embarque.data_prevista_embarque) : '-'}
                            </div>
                        </div>
                    </div>
            `;
        }

        html += `
                    <!-- Produtos -->
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="mb-0">Produtos (${separacao.produtos.length})</h6>
                        ${separacao.produtos.length > 5 ? `
                            <button class="btn btn-link btn-sm p-0" onclick="window.modalSeparacoes.toggleProdutosSeparacao('${separacao.separacao_lote_id}')">
                                <span id="btn-modal-toggle-${separacao.separacao_lote_id}">Ver todos</span>
                            </button>
                        ` : ''}
                    </div>
                    <div class="table-responsive" id="produtos-tabela-${separacao.separacao_lote_id}">
                        <table class="table table-sm table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th>Código</th>
                                    <th>Produto</th>
                                    <th class="text-end">Quantidade</th>
                                    <th class="text-end">Valor</th>
                                    <th class="text-end">Peso</th>
                                    <th class="text-end">Pallet</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        // Renderizar produtos (mostrar apenas 5 inicialmente se tiver mais)
        const produtosVisiveis = separacao.produtos.length > 5 ? 5 : separacao.produtos.length;
        separacao.produtos.slice(0, produtosVisiveis).forEach(produto => {
            html += `
                                <tr class="produto-visivel-${separacao.separacao_lote_id}">
                                    <td>${produto.cod_produto}</td>
                                    <td>${produto.nome_produto || '-'}</td>
                                    <td class="text-end">${this.formatarQuantidade(produto.qtd_saldo)}</td>
                                    <td class="text-end">${this.formatarMoeda(produto.valor_saldo)}</td>
                                    <td class="text-end">${this.formatarPeso(produto.peso)}</td>
                                    <td class="text-end">${this.formatarPallet(produto.pallet)}</td>
                                </tr>
            `;
        });
        
        // Renderizar produtos ocultos
        if (separacao.produtos.length > 5) {
            separacao.produtos.slice(5).forEach(produto => {
                html += `
                                <tr class="produto-oculto-${separacao.separacao_lote_id}" style="display: none;">
                                    <td>${produto.cod_produto}</td>
                                    <td>${produto.nome_produto || '-'}</td>
                                    <td class="text-end">${this.formatarQuantidade(produto.qtd_saldo)}</td>
                                    <td class="text-end">${this.formatarMoeda(produto.valor_saldo)}</td>
                                    <td class="text-end">${this.formatarPeso(produto.peso)}</td>
                                    <td class="text-end">${this.formatarPallet(produto.pallet)}</td>
                                </tr>
                `;
            });
        }

        // Totais da separação
        html += `
                            </tbody>
                            <tfoot class="table-secondary">
                                <tr>
                                    <th colspan="2">Totais</th>
                                    <th class="text-end">${separacao.produtos.length} itens</th>
                                    <th class="text-end">${this.formatarMoeda(separacao.valor_total)}</th>
                                    <th class="text-end">${this.formatarPeso(separacao.peso_total)}</th>
                                    <th class="text-end">${this.formatarPallet(separacao.pallet_total)}</th>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            </div>
        `;

        return html;
    }

    renderizarPaginacao() {
        const totalPaginas = Math.ceil(this.separacoes.length / this.separacoesPorPagina);
        
        if (totalPaginas <= 1) return '';

        let html = `
            <nav aria-label="Navegação de separações">
                <ul class="pagination justify-content-center">
                    <li class="page-item ${this.paginaAtual === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="window.modalSeparacoes.irParaPagina(${this.paginaAtual - 1}); return false;">
                            <i class="fas fa-chevron-left"></i>
                        </a>
                    </li>
        `;

        // Páginas
        for (let i = 1; i <= totalPaginas; i++) {
            html += `
                    <li class="page-item ${i === this.paginaAtual ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="window.modalSeparacoes.irParaPagina(${i}); return false;">${i}</a>
                    </li>
            `;
        }

        html += `
                    <li class="page-item ${this.paginaAtual === totalPaginas ? 'disabled' : ''}">
                        <a class="page-link" href="#" onclick="window.modalSeparacoes.irParaPagina(${this.paginaAtual + 1}); return false;">
                            <i class="fas fa-chevron-right"></i>
                        </a>
                    </li>
                </ul>
            </nav>
        `;

        return html;
    }

    irParaPagina(pagina) {
        const totalPaginas = Math.ceil(this.separacoes.length / this.separacoesPorPagina);
        
        if (pagina < 1) pagina = 1;
        if (pagina > totalPaginas) pagina = totalPaginas;
        
        this.paginaAtual = pagina;
        this.renderizarSeparacoes();
    }

    calcularTotaisGerais() {
        return this.separacoes.reduce((totais, sep) => {
            totais.valor += sep.valor_total || 0;
            totais.peso += sep.peso_total || 0;
            totais.pallet += sep.pallet_total || 0;
            return totais;
        }, { valor: 0, peso: 0, pallet: 0 });
    }

    getStatusClass(status) {
        const statusMap = {
            'ABERTO': 'warning',
            'FATURADO': 'info',
            'COTADO': 'primary',
            'EMBARCADO': 'success',
            'NF no CD': 'secondary'
        };
        return statusMap[status] || 'secondary';
    }

    getStatusBadge(status) {
        const statusClass = this.getStatusClass(status);
        return `<span class="badge bg-${statusClass}">${status}</span>`;
    }

    mostrarErro(mensagem) {
        const container = document.getElementById('modal-separacoes-content');
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${mensagem}
            </div>
        `;
        document.getElementById('modal-separacoes-loading').style.display = 'none';
        container.style.display = 'block';
    }

    // Formatadores
    formatarMoeda(valor) {
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarPeso(peso) {
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }

    formatarQuantidade(qtd) {
        if (!qtd) return '0';
        return parseFloat(qtd).toFixed(0);
    }

    formatarData(data) {
        if (!data) return '-';
        const d = new Date(data + 'T00:00:00');
        return d.toLocaleDateString('pt-BR');
    }

    toggleProdutosSeparacao(loteId) {
        const produtosOcultos = document.querySelectorAll(`.produto-oculto-${loteId}`);
        const btnToggle = document.getElementById(`btn-modal-toggle-${loteId}`);
        
        if (produtosOcultos.length > 0 && btnToggle) {
            const isHidden = produtosOcultos[0].style.display === 'none';
            
            produtosOcultos.forEach(tr => {
                tr.style.display = isHidden ? '' : 'none';
            });
            
            btnToggle.textContent = isHidden ? 'Ver menos' : 'Ver todos';
        }
    }
}

// Função global para abrir o modal
window.abrirModalSeparacoes = function(numPedido) {
    if (!window.modalSeparacoes) {
        window.modalSeparacoes = new ModalSeparacoes();
    }
    window.modalSeparacoes.abrir(numPedido);
};

// Disponibilizar globalmente
window.ModalSeparacoes = ModalSeparacoes;