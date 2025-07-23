/**
 * 🎯 WORKSPACE CORE - Funcionalidades centrais
 * Gerenciamento principal e coordenação entre módulos
 */

class WorkspaceCore {
    constructor() {
        this.preSeparacoes = new Map(); // loteId -> {produtos: [], totais: {}}
        this.produtosSelecionados = new Set();
        this.dadosProdutos = new Map(); // codProduto -> dados completos
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('✅ Workspace Core inicializado');
    }

    setupEventListeners() {
        // Detectar quando o dropdown de detalhes é aberto
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-expandir')) {
                const btn = e.target.closest('.btn-expandir');
                const numPedido = btn.dataset.pedido;
                this.abrirWorkspace(numPedido);
            }
        });
    }

    async abrirWorkspace(numPedido) {
        console.log(`🔄 Carregando workspace para pedido ${numPedido}`);
        
        try {
            // Carregar dados do workspace
            const workspaceResponse = await fetch(`/carteira/api/pedido/${numPedido}/workspace`);
            const workspaceData = await workspaceResponse.json();

            if (!workspaceResponse.ok || !workspaceData.success) {
                throw new Error(workspaceData.error || 'Erro ao carregar workspace');
            }

            // Armazenar dados dos produtos
            workspaceData.produtos.forEach(produto => {
                this.dadosProdutos.set(produto.cod_produto, produto);
            });

            // Carregar pré-separações existentes usando o manager
            const preSeparacoesData = await this.carregarPreSeparacoes(numPedido);
            
            if (preSeparacoesData.success && preSeparacoesData.lotes) {
                // Processar pré-separações carregadas
                const preSeparacoesMap = this.processarPreSeparacoesCarregadas(preSeparacoesData.lotes);
                
                // Atualizar Map local
                preSeparacoesMap.forEach((value, key) => {
                    this.preSeparacoes.set(key, value);
                });
                
                console.log(`✅ Carregadas ${preSeparacoesData.lotes.length} pré-separações existentes`);
            }

            // Renderizar workspace no container de detalhes
            const contentDiv = document.getElementById(`content-${numPedido}`);
            const loadingDiv = document.getElementById(`loading-${numPedido}`);
            
            if (contentDiv) {
                contentDiv.innerHTML = this.renderizarWorkspace(numPedido, workspaceData);
                contentDiv.style.display = 'block';
            }
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
            }

            // Renderizar lotes existentes se houver
            if (preSeparacoesData.success && preSeparacoesData.lotes) {
                await this.renderizarLotesExistentes(numPedido, preSeparacoesData.lotes);
            }

            // Inicializar módulos dependentes
            if (window.workspaceDragDrop) {
                window.workspaceDragDrop.configurarDragDrop(numPedido);
            }

        } catch (error) {
            console.error(`❌ Erro ao carregar workspace:`, error);
            this.renderizarErroWorkspace(numPedido, error.message);
        }
    }

    async carregarPreSeparacoes(numPedido) {
        try {
            const response = await fetch(`/carteira/api/pedido/${numPedido}/pre-separacoes`);
            return await response.json();
        } catch (error) {
            console.error('Erro ao carregar pré-separações:', error);
            return { success: false, lotes: [] };
        }
    }

    processarPreSeparacoesCarregadas(lotes) {
        const preSeparacoesMap = new Map();
        
        lotes.forEach(lote => {
            const loteData = {
                loteId: lote.lote_id,
                produtos: lote.produtos || [],
                totais: lote.totais || { valor: 0, peso: 0, pallet: 0 },
                status: lote.status || 'criado',
                expedicao: lote.expedicao,
                agendamento: lote.agendamento,
                protocolo: lote.protocolo
            };
            
            preSeparacoesMap.set(lote.lote_id, loteData);
        });
        
        return preSeparacoesMap;
    }

    renderizarWorkspace(numPedido, data) {
        return `
            <div class="workspace-montagem" data-pedido="${numPedido}">
                <!-- Header do Workspace -->
                <div class="workspace-header bg-primary text-white p-3 rounded-top">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h5 class="mb-0">
                                <i class="fas fa-boxes me-2"></i>
                                Workspace de Montagem - Pedido ${numPedido}
                            </h5>
                            <small>Arraste os produtos para os lotes de pré-separação</small>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="workspace-resumo">
                                <strong>Total: ${this.formatarMoeda(data.valor_total || 0)}</strong>
                                <br><small>${data.produtos.length} produtos</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabela de Produtos (Origem) -->
                <div class="workspace-produtos bg-light p-3">
                    <h6 class="mb-3">
                        <i class="fas fa-list me-2"></i>
                        Produtos do Pedido
                    </h6>
                    ${window.workspaceTabela ? window.workspaceTabela.renderizarTabelaProdutos(data.produtos) : this.renderizarTabelaFallback(data.produtos)}
                </div>

                <!-- Área de Lotes (Destino) -->
                <div class="workspace-lotes p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6 class="mb-0">
                            <i class="fas fa-layer-group me-2"></i>
                            Pré-Separações
                        </h6>
                        <button class="btn btn-success btn-sm" onclick="workspace.criarNovoLote('${numPedido}')">
                            <i class="fas fa-plus me-1"></i> Novo Lote
                        </button>
                    </div>
                    <div class="lotes-container row" id="lotes-container-${numPedido}">
                        <!-- Lotes serão criados dinamicamente -->
                        <div class="col-md-4">
                            <div class="card lote-placeholder border-dashed text-center p-4">
                                <i class="fas fa-plus fa-2x text-muted mb-2"></i>
                                <p class="text-muted mb-0">Clique em "Novo Lote" ou arraste produtos aqui</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async renderizarLotesExistentes(numPedido, lotes) {
        const container = document.getElementById(`lotes-container-${numPedido}`);
        if (!container || lotes.length === 0) return;

        // Remover placeholder
        const placeholder = container.querySelector('.lote-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Renderizar cada lote existente
        for (const lote of lotes) {
            const loteCard = document.createElement('div');
            loteCard.className = 'col-md-4 mb-3';
            loteCard.innerHTML = window.workspaceLotes ? window.workspaceLotes.renderizarCardPreSeparacao(lote) : '';
            container.appendChild(loteCard);

            // Configurar drop zone
            const newCard = loteCard.querySelector('.lote-card');
            if (window.workspaceDragDrop) {
                window.workspaceDragDrop.reconfigurarDropZone(newCard);
            }
        }

        console.log(`✅ Renderizados ${lotes.length} lotes de pré-separação`);
    }

    renderizarErroWorkspace(numPedido, mensagem) {
        const contentDiv = document.getElementById(`content-${numPedido}`);
        const loadingDiv = document.getElementById(`loading-${numPedido}`);
        
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Erro ao carregar workspace</strong>
                    <p class="mb-2">${mensagem}</p>
                    <button class="btn btn-sm btn-outline-danger" onclick="location.reload()">
                        <i class="fas fa-redo me-1"></i> Recarregar página
                    </button>
                </div>
            `;
            contentDiv.style.display = 'block';
        }
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
        }
    }

    renderizarTabelaFallback(produtos) {
        return `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Módulo de tabela não carregado. ${produtos.length} produtos encontrados.
            </div>
        `;
    }

    // Utilitários
    formatarMoeda(valor) {
        if (!valor) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    formatarQuantidade(qtd) {
        if (!qtd) return '0';
        return Math.floor(qtd).toLocaleString('pt-BR');
    }

    formatarPeso(peso) {
        if (!peso) return '0 kg';
        return `${parseFloat(peso).toFixed(1)} kg`;
    }

    formatarPallet(pallet) {
        if (!pallet) return '0 plt';
        return `${parseFloat(pallet).toFixed(2)} plt`;
    }
}

// Disponibilizar globalmente
window.WorkspaceCore = WorkspaceCore;