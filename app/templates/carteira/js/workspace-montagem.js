/**
 * 🎯 WORKSPACE DE MONTAGEM DE CARGA
 * Sistema de pré-separação com drag & drop
 */

class WorkspaceMontagem {
    constructor() {
        this.preSeparacoes = new Map(); // loteId -> {produtos: [], totais: {}}
        this.produtosSelecionados = new Set();
        this.dadosProdutos = new Map(); // codProduto -> dados completos
        
        // Inicializar módulos
        this.dragDropHandler = new DragDropHandler(this);
        this.loteManager = new LoteManager(this);
        this.modalCardex = new ModalCardex();
        this.preSeparacaoManager = new PreSeparacaoManager(this);
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('✅ Workspace de Montagem inicializado');
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
            const preSeparacoesData = await this.preSeparacaoManager.carregarPreSeparacoes(numPedido);
            
            if (preSeparacoesData.success && preSeparacoesData.lotes) {
                // Processar pré-separações carregadas
                const preSeparacoesMap = this.preSeparacaoManager.processarPreSeparacoesCarregadas(preSeparacoesData.lotes);
                
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

            // Configurar drag & drop usando requestAnimationFrame para garantir renderização
            requestAnimationFrame(() => {
                console.log('🎯 Inicializando drag & drop...');
                this.dragDropHandler.configurarDragDrop(numPedido);
                
                // Verificar se elementos foram marcados corretamente
                const produtos = document.querySelectorAll(`.workspace-montagem[data-pedido="${numPedido}"] .produto-origem`);
                const dropZones = document.querySelectorAll(`.workspace-montagem[data-pedido="${numPedido}"] .drop-zone`);
                console.log(`✅ Configuração completa: ${produtos.length} produtos, ${dropZones.length} drop zones`);
            });

        } catch (error) {
            console.error(`❌ Erro ao carregar workspace:`, error);
            this.renderizarErroWorkspace(numPedido, error.message);
        }
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
            loteCard.innerHTML = this.loteManager.renderizarCardPreSeparacao(lote);
            container.appendChild(loteCard);

            // Configurar drop zone
            const newCard = loteCard.querySelector('.lote-card');
            this.dragDropHandler.reconfigurarDropZone(newCard);
        }

        console.log(`✅ Renderizados ${lotes.length} lotes de pré-separação`);
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
                    ${this.renderizarTabelaProdutos(data.produtos)}
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
                            <div class="card lote-placeholder border-dashed text-center p-4" data-lote-id="placeholder">
                                <i class="fas fa-plus fa-2x text-muted mb-2"></i>
                                <p class="text-muted mb-0">Clique em "Novo Lote" ou arraste produtos aqui</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderizarTabelaProdutos(produtos) {
        // Delegado para WorkspaceTabela
        if (window.workspaceTabela) {
            return window.workspaceTabela.renderizarTabelaProdutos(produtos);
        }
        return `<div class="alert alert-warning">Módulo de tabela não carregado</div>`;
    }

    calcularStatusDisponibilidade(produto) {
        if (produto.estoque_hoje >= produto.qtd_pedido) {
            return { classe: 'bg-success', texto: 'Hoje' };
        }
        
        if (produto.data_disponibilidade) {
            const diasAte = this.calcularDiasAte(produto.data_disponibilidade);
            if (diasAte <= 7) {
                return { classe: 'bg-warning', texto: `${diasAte}d` };
            }
        }
        
        return { classe: 'bg-danger', texto: 'Sem est.' };
    }

    calcularDiasAte(dataStr) {
        const hoje = new Date();
        const dataTarget = new Date(dataStr);
        const diffTime = dataTarget - hoje;
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }

    /**
     * 🎯 CALCULAR SALDO DISPONÍVEL DO PRODUTO
     * Fórmula: Qtd Pedido - Qtd em Separações - Qtd em Pré-Separações
     */
    calcularSaldoDisponivel(produto) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            return window.workspaceQuantidades.calcularSaldoDisponivel(produto);
        }
        return { qtdEditavel: 0, qtdIndisponivel: produto.qtd_pedido || 0 };
    }

    // Delegação para LoteManager

    gerarNovoLoteId() {
        return this.loteManager.gerarNovoLoteId();
    }

    criarNovoLote(numPedido) {
        this.loteManager.criarNovoLote(numPedido);
    }

    criarLote(numPedido, loteId) {
        this.loteManager.criarLote(numPedido, loteId);
    }
    
    removerProdutoDoLote(loteId, codProduto) {
        this.loteManager.removerProdutoDoLote(loteId, codProduto);
    }
    
    obterNumeroPedido() {
        // Buscar o número do pedido do workspace ativo
        const workspaceElement = document.querySelector('.workspace-montagem[data-pedido]');
        return workspaceElement ? workspaceElement.dataset.pedido : null;
    }
    
    resetarQuantidadeProduto(codProduto) {
        const input = document.querySelector(`input[data-produto="${codProduto}"]`);
        if (input) {
            const qtdOriginal = parseInt(input.dataset.qtdOriginal) || 0;
            input.value = qtdOriginal;
            input.dataset.qtdSaldo = qtdOriginal;
            
            // Atualizar span
            const spanSaldo = input.nextElementSibling;
            if (spanSaldo) {
                spanSaldo.textContent = `/${qtdOriginal}`;
            }
            
            // Atualizar valores calculados
            if (window.workspaceQuantidades) {
                window.workspaceQuantidades.atualizarQuantidadeProduto(input);
            }
        }
    }

    // Delegação para LoteManager (método removido - usar this.loteManager.renderizarCardLote)

    // Delegação para LoteManager (método removido - usar this.loteManager.renderizarProdutosDoLote)

    adicionarProdutoNoLote(loteId, dadosProduto) {
        this.loteManager.adicionarProdutoNoLote(loteId, dadosProduto);
        
        // 🎯 ATUALIZAR SALDO DISPONÍVEL NA TABELA
        this.atualizarSaldoNaTabela(dadosProduto.codProduto);
    }
    
    /**
     * 🎯 ATUALIZAR SALDO DISPONÍVEL NA TABELA APÓS MUDANÇAS
     */
    atualizarSaldoNaTabela(codProduto) {
        const dadosProduto = this.dadosProdutos.get(codProduto);
        if (!dadosProduto) return;
        
        // Recalcular saldo disponível
        const saldoDisponivel = this.calcularSaldoDisponivel(dadosProduto);
        
        // Encontrar input de quantidade na tabela
        const input = document.querySelector(`input[data-produto="${codProduto}"]`);
        if (input) {
            // Atualizar atributos do input
            input.dataset.qtdSaldo = Math.floor(saldoDisponivel.qtdEditavel);
            input.max = Math.floor(saldoDisponivel.qtdEditavel);
            
            // Atualizar o valor se exceder o novo saldo
            const valorAtual = parseInt(input.value) || 0;
            if (valorAtual > saldoDisponivel.qtdEditavel) {
                input.value = Math.floor(saldoDisponivel.qtdEditavel);
                this.atualizarQuantidadeProduto(input);
            }
            
            // Atualizar o span do saldo
            const spanSaldo = input.nextElementSibling;
            if (spanSaldo) {
                spanSaldo.textContent = `/${Math.floor(saldoDisponivel.qtdEditavel)}`;
                spanSaldo.title = `Saldo disponível: ${this.formatarQuantidade(saldoDisponivel.qtdEditavel)} de ${this.formatarQuantidade(dadosProduto.qtd_pedido)} do pedido`;
                
                // Visual feedback se saldo mudou
                if (saldoDisponivel.temRestricao) {
                    spanSaldo.classList.add('text-warning');
                } else {
                    spanSaldo.classList.remove('text-warning');
                }
            }
        }
    }

    // Delegação para LoteManager (método removido - usar this.loteManager.recalcularTotaisLote)

    // Delegação para LoteManager (método removido - usar this.loteManager.atualizarCardLote)

    async abrirCardex(codProduto) {
        await this.modalCardex.abrirCardex(codProduto, this.dadosProdutos);
    }

    atualizarQuantidadeProduto(input) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            window.workspaceQuantidades.atualizarQuantidadeProduto(input);
        }
    }
    
    atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            window.workspaceQuantidades.atualizarColunasCalculadas(codProduto, novaQtd, dadosProduto);
        }
    }
    
    recalcularTotaisLotesComProduto(codProduto) {
        // Delegado para WorkspaceQuantidades
        if (window.workspaceQuantidades) {
            window.workspaceQuantidades.recalcularTotaisLotesComProduto(codProduto);
        }
    }

    // Delegação para ModalCardex (método removido - usar this.modalCardex.mostrarModalCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.renderizarModalCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.renderizarLinhasCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.getStatusClasseCardex)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.renderizarAlertas)

    // Delegação para ModalCardex (método removido - usar this.modalCardex.formatarData)

    exportarCardex(codProduto) {
        this.modalCardex.exportarCardex(codProduto);
    }

    async gerarSeparacao(loteId) {
        console.log(`⚡ Gerar separação para lote ${loteId}`);
        
        const loteData = this.preSeparacoes.get(loteId);
        if (!loteData || loteData.produtos.length === 0) {
            alert('❌ Lote vazio! Adicione produtos antes de gerar a separação.');
            return;
        }

        // Obter número do pedido
        const numPedido = this.obterNumeroPedido();
        if (!numPedido) {
            alert('❌ Não foi possível identificar o número do pedido.');
            return;
        }

        // 🎯 DELEGAR PARA SEPARACAO-MANAGER (Caso 1 - Criar separação completa)
        if (window.separacaoManager) {
            await window.separacaoManager.criarSeparacaoCompleta(numPedido);
            
            // Se a separação foi criada, remover o lote local
            this.loteManager.removerLote(loteId);
        } else {
            console.error('❌ Separação Manager não disponível');
            alert('❌ Sistema de separação não está disponível');
        }
    }

    async confirmarSeparacao(loteId) {
        console.log(`🔄 Confirmar separação para lote ${loteId}`);
        
        // 🎯 DELEGAR PARA SEPARACAO-MANAGER (Caso 2 - Transformar pré-separação em separação)
        if (window.separacaoManager) {
            await window.separacaoManager.transformarLoteEmSeparacao(null, loteId);
            
            // Se a transformação foi bem-sucedida, remover o lote local
            this.loteManager.removerLote(loteId);
        } else {
            console.error('❌ Separação Manager não disponível');
            alert('❌ Sistema de separação não está disponível');
        }
    }


    obterNumeroPedido() {
        // Extrair número do pedido do workspace atual
        const workspaceElement = document.querySelector('.workspace-montagem[data-pedido]');
        return workspaceElement ? workspaceElement.dataset.pedido : null;
    }


    abrirDetalhesLote(loteId) {
        console.log(`🔍 Abrir detalhes do lote ${loteId}`);
        // Modal com detalhes do lote já implementado via card expandido
        const loteData = this.preSeparacoes.get(loteId);
        if (loteData) {
            const cardElement = document.querySelector(`[data-lote-id="${loteId}"]`);
            if (cardElement) {
                cardElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }

    removerLote(loteId) {
        this.loteManager.removerLote(loteId);
    }

    removerProdutoDoLote(loteId, codProduto) {
        this.loteManager.removerProdutoDoLote(loteId, codProduto);
        
        // 🎯 ATUALIZAR SALDO DISPONÍVEL NA TABELA
        this.atualizarSaldoNaTabela(codProduto);
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
        // Para quantidades, sempre mostrar como inteiro
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
window.WorkspaceMontagem = WorkspaceMontagem;