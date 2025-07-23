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

            // Configurar drag & drop
            this.dragDropHandler.configurarDragDrop(numPedido);

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

    renderizarTabelaProdutos(produtos) {
        let html = `
            <div class="table-responsive">
                <table class="table table-sm table-hover workspace-produtos-table">
                    <thead class="table-dark">
                        <tr>
                            <th width="30px"><i class="fas fa-grip-vertical"></i></th>
                            <th>Produto</th>
                            <th>Pedido</th>
                            <th>Est.Hoje</th>
                            <th>Est.7D</th>
                            <th>Est.Exp</th>
                            <th>Disponível</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        produtos.forEach(produto => {
            const statusDisponibilidade = this.calcularStatusDisponibilidade(produto);
            
            html += `
                <tr class="produto-origem" 
                    draggable="true" 
                    data-produto="${produto.cod_produto}"
                    data-qtd-pedido="${produto.qtd_pedido}">
                    
                    <td class="drag-handle text-center">
                        <i class="fas fa-grip-vertical text-muted"></i>
                    </td>
                    
                    <td>
                        <div class="produto-info">
                            <strong class="text-primary">${produto.cod_produto}</strong>
                            <br><small class="text-muted">${produto.nome_produto || ''}</small>
                        </div>
                    </td>
                    
                    <td class="text-end">
                        <div class="input-group input-group-sm" style="max-width: 120px;">
                            <input type="number" 
                                   class="form-control form-control-sm text-end qtd-editavel" 
                                   value="${Math.floor(produto.qtd_pedido)}"
                                   min="0"
                                   max="${Math.floor(produto.qtd_pedido)}"
                                   step="1"
                                   data-produto="${produto.cod_produto}"
                                   data-qtd-original="${Math.floor(produto.qtd_pedido)}"
                                   onchange="workspace.atualizarQuantidadeProduto(this)"
                                   title="Quantidade editável para separação parcial (apenas números inteiros)">
                            <span class="input-group-text" title="De ${this.formatarQuantidade(produto.qtd_pedido)}">
                                <i class="fas fa-edit text-primary"></i>
                            </span>
                        </div>
                    </td>
                    
                    <td class="text-end">
                        <span class="badge ${produto.estoque_hoje > 0 ? 'bg-success' : 'bg-danger'}"
                              title="Estoque atual: ${this.formatarQuantidade(produto.estoque_hoje)} unidades
Necessário para pedido: ${this.formatarQuantidade(produto.qtd_pedido)} unidades
${produto.estoque_hoje >= produto.qtd_pedido ? '✅ Estoque suficiente' : '⚠️ Estoque insuficiente'}">
                            ${this.formatarQuantidade(produto.estoque_hoje)}
                        </span>
                    </td>
                    
                    <td class="text-end">
                        <span class="badge ${produto.menor_estoque_7d > 0 ? 'bg-info' : 'bg-warning'}"
                              title="Menor estoque nos próximos 7 dias: ${this.formatarQuantidade(produto.menor_estoque_7d)} unidades
📈 Previsão de ruptura baseada em saídas programadas
${produto.menor_estoque_7d <= 0 ? '🚨 Possível ruptura em 7 dias' : '✅ Estoque mantido por 7 dias'}">
                            ${this.formatarQuantidade(produto.menor_estoque_7d)}
                        </span>
                    </td>
                    
                    <td class="text-end">
                        <span class="badge ${produto.estoque_data_expedicao > 0 ? 'bg-success' : 'bg-secondary'}"
                              title="Estoque previsto na data de expedição: ${this.formatarQuantidade(produto.estoque_data_expedicao)} unidades
📅 Data expedição: ${produto.data_disponibilidade || 'Não definida'}
${produto.estoque_data_expedicao >= produto.qtd_pedido ? '✅ Disponível na expedição' : '⚠️ Insuficiente na expedição'}">
                            ${this.formatarQuantidade(produto.estoque_data_expedicao)}
                        </span>
                    </td>
                    
                    <td>
                        <span class="badge ${statusDisponibilidade.classe}">
                            ${statusDisponibilidade.texto}
                        </span>
                    </td>
                    
                    <td>
                        <button class="btn btn-sm btn-outline-info" 
                                onclick="workspace.abrirCardex('${produto.cod_produto}')"
                                title="Ver cardex completo">
                            <i class="fas fa-search"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        return html;
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

    // Delegação para LoteManager (método removido - usar this.loteManager.renderizarCardLote)

    // Delegação para LoteManager (método removido - usar this.loteManager.renderizarProdutosDoLote)

    adicionarProdutoNoLote(loteId, dadosProduto) {
        this.loteManager.adicionarProdutoNoLote(loteId, dadosProduto);
    }

    // Delegação para LoteManager (método removido - usar this.loteManager.recalcularTotaisLote)

    // Delegação para LoteManager (método removido - usar this.loteManager.atualizarCardLote)

    async abrirCardex(codProduto) {
        await this.modalCardex.abrirCardex(codProduto, this.dadosProdutos);
    }

    atualizarQuantidadeProduto(input) {
        const codProduto = input.dataset.produto;
        const qtdOriginal = parseInt(input.dataset.qtdOriginal);
        let novaQtd = parseInt(input.value) || 0;
        
        // Garantir que é número inteiro
        if (!Number.isInteger(novaQtd)) {
            novaQtd = Math.floor(novaQtd);
            input.value = novaQtd;
        }
        
        // Validar limites
        if (novaQtd < 0) {
            input.value = 0;
            return;
        }
        if (novaQtd > qtdOriginal) {
            input.value = qtdOriginal;
            alert(`⚠️ Quantidade não pode exceder o pedido original (${qtdOriginal} unidades)`);
            return;
        }
        
        // Atualizar dados do produto
        const dadosProduto = this.dadosProdutos.get(codProduto);
        if (dadosProduto) {
            dadosProduto.qtd_selecionada = novaQtd;
            
            // Recalcular peso e pallet proporcionalmente
            const fatorProporcional = novaQtd / qtdOriginal;
            dadosProduto.peso_selecionado = dadosProduto.peso_unitario * novaQtd;
            dadosProduto.pallet_selecionado = dadosProduto.pallet_unitario * novaQtd;
            dadosProduto.valor_selecionado = dadosProduto.preco_unitario * novaQtd;
            
            console.log(`✅ Quantidade atualizada: ${codProduto} = ${novaQtd}`);
            
            // Se produto está em algum lote, recalcular totais
            this.recalcularTotaisLotesComProduto(codProduto);
        }
        
        // Visual feedback
        input.classList.add('bg-warning');
        setTimeout(() => input.classList.remove('bg-warning'), 1000);
    }
    
    recalcularTotaisLotesComProduto(codProduto) {
        this.preSeparacoes.forEach((loteData, loteId) => {
            const produtoNoLote = loteData.produtos.find(p => p.codProduto === codProduto);
            if (produtoNoLote) {
                // Atualizar dados do produto no lote
                const dadosProduto = this.dadosProdutos.get(codProduto);
                if (dadosProduto) {
                    produtoNoLote.qtd = dadosProduto.qtd_selecionada || dadosProduto.qtd_pedido;
                    produtoNoLote.peso = dadosProduto.peso_selecionado || dadosProduto.peso_total;
                    produtoNoLote.pallet = dadosProduto.pallet_selecionado || dadosProduto.pallet_total;
                    produtoNoLote.valor = dadosProduto.valor_selecionado || dadosProduto.valor_total;
                }
                
                // Recalcular totais do lote
                this.loteManager.recalcularTotaisLote(loteId);
                this.loteManager.atualizarCardLote(loteId);
            }
        });
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

        // Coletar dados necessários
        const numPedido = this.obterNumeroPedido();
        if (!numPedido) {
            alert('❌ Não foi possível identificar o número do pedido.');
            return;
        }

        // Solicitar dados de expedição/agendamento
        const dadosExpedicao = await this.solicitarDadosExpedicao(loteId);
        if (!dadosExpedicao) {
            return; // Usuário cancelou
        }

        try {
            // Preparar payload para a API
            const payload = {
                num_pedido: numPedido,
                lotes: [{
                    lote_id: loteId,
                    produtos: loteData.produtos.map(produto => ({
                        cod_produto: produto.codProduto,
                        quantidade: produto.quantidade
                    })),
                    expedicao: dadosExpedicao.expedicao,
                    agendamento: dadosExpedicao.agendamento || null,
                    protocolo: dadosExpedicao.protocolo || null
                }]
            };

            // Enviar para API
            const response = await fetch('/carteira/api/workspace/gerar-separacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                alert(`✅ ${result.message}`);
                
                // Remover lote do workspace após sucesso
                this.loteManager.removerLote(loteId);
                
                // Mostrar resumo
                if (result.lotes_processados && result.lotes_processados.length > 0) {
                    const loteInfo = result.lotes_processados[0];
                    console.log(`📊 Separação criada:
- Tipo: ${loteInfo.tipo_envio.toUpperCase()}
- Produtos: ${loteInfo.total_produtos}
- Valor: R$ ${loteInfo.total_valor.toFixed(2)}
- Peso: ${loteInfo.total_peso.toFixed(1)} kg
- Pallets: ${loteInfo.total_pallet.toFixed(2)}`);
                }
                
            } else {
                alert(`❌ Erro: ${result.error}`);
            }

        } catch (error) {
            console.error('❌ Erro ao gerar separação:', error);
            alert('❌ Erro de comunicação com o servidor');
        }
    }

    async confirmarSeparacao(loteId) {
        console.log(`✅ Confirmar separação de pré-separação ${loteId}`);
        
        // Solicitar dados de agendamento/protocolo
        const dadosConfirmacao = await this.solicitarDadosConfirmacao(loteId);
        if (!dadosConfirmacao) {
            return; // Usuário cancelou
        }

        try {
            // Chamar API para confirmar pré-separação como separação
            const response = await fetch(`/carteira/api/pre-separacao/lote/${loteId}/confirmar-separacao`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agendamento: dadosConfirmacao.agendamento,
                    protocolo: dadosConfirmacao.protocolo
                })
            });

            const result = await response.json();

            if (result.success) {
                alert(`✅ ${result.message}`);
                
                // Atualizar status do lote localmente
                const loteData = this.preSeparacoes.get(loteId);
                if (loteData) {
                    loteData.status = 'separacao';
                    loteData.produtos.forEach(p => p.status = 'separacao');
                    
                    // Re-renderizar o card
                    const cardElement = document.querySelector(`[data-lote-id="${loteId}"]`);
                    if (cardElement) {
                        cardElement.outerHTML = this.loteManager.renderizarCardPreSeparacao(loteData);
                    }
                }
                
                console.log(`📊 Separação confirmada: ${result.separacao_lote_id}`);
                
            } else {
                alert(`❌ Erro: ${result.error}`);
            }

        } catch (error) {
            console.error('❌ Erro ao confirmar separação:', error);
            alert('❌ Erro de comunicação com o servidor');
        }
    }

    async solicitarDadosConfirmacao(loteId) {
        return new Promise((resolve) => {
            // Criar modal simples para dados de confirmação
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-check-circle me-2"></i>
                                Confirmar Separação
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                Transformando pré-separação em separação definitiva
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Data de Agendamento</label>
                                <input type="date" class="form-control" id="agendamento-input">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Protocolo</label>
                                <input type="text" class="form-control" id="protocolo-input" placeholder="Protocolo de agendamento">
                            </div>
                            <small class="text-muted">
                                <i class="fas fa-info-circle me-1"></i>
                                Lote: ${loteId}
                            </small>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-action="cancel">Cancelar</button>
                            <button type="button" class="btn btn-success" data-action="confirm">
                                <i class="fas fa-check me-1"></i>
                                Confirmar Separação
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();

            // Event listeners
            modal.addEventListener('click', (e) => {
                if (e.target.dataset.action === 'cancel') {
                    bsModal.hide();
                    resolve(null);
                } else if (e.target.dataset.action === 'confirm') {
                    const agendamento = document.getElementById('agendamento-input').value;
                    const protocolo = document.getElementById('protocolo-input').value;

                    bsModal.hide();
                    resolve({
                        agendamento: agendamento || null,
                        protocolo: protocolo || null
                    });
                }
            });

            // Remover modal ao fechar
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
            });
        });
    }

    obterNumeroPedido() {
        // Extrair número do pedido do workspace atual
        const workspaceElement = document.querySelector('.workspace-montagem[data-pedido]');
        return workspaceElement ? workspaceElement.dataset.pedido : null;
    }

    async solicitarDadosExpedicao(loteId) {
        return new Promise((resolve) => {
            // Criar modal simples para coletar dados
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-shipping-fast me-2"></i>
                                Dados da Separação
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Data de Expedição <span class="text-danger">*</span></label>
                                <input type="date" class="form-control" id="expedicao-input" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Data de Agendamento</label>
                                <input type="date" class="form-control" id="agendamento-input">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Protocolo</label>
                                <input type="text" class="form-control" id="protocolo-input" placeholder="Protocolo de agendamento">
                            </div>
                            <small class="text-muted">
                                <i class="fas fa-info-circle me-1"></i>
                                Lote: ${loteId}
                            </small>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-action="cancel">Cancelar</button>
                            <button type="button" class="btn btn-primary" data-action="confirm">
                                <i class="fas fa-check me-1"></i>
                                Gerar Separação
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();

            // Pré-preencher data de expedição com hoje + 1 dia
            const amanha = new Date();
            amanha.setDate(amanha.getDate() + 1);
            document.getElementById('expedicao-input').value = amanha.toISOString().split('T')[0];

            // Event listeners
            modal.addEventListener('click', (e) => {
                if (e.target.dataset.action === 'cancel') {
                    bsModal.hide();
                    resolve(null);
                } else if (e.target.dataset.action === 'confirm') {
                    const expedicao = document.getElementById('expedicao-input').value;
                    const agendamento = document.getElementById('agendamento-input').value;
                    const protocolo = document.getElementById('protocolo-input').value;

                    if (!expedicao) {
                        alert('❌ Data de expedição é obrigatória!');
                        return;
                    }

                    bsModal.hide();
                    resolve({
                        expedicao,
                        agendamento,
                        protocolo
                    });
                }
            });

            // Remover modal ao fechar
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
            });
        });
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