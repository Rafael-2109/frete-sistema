/**
 * 🎯 DRAG & DROP HANDLER - VERSÃO REFATORADA
 * Sistema robusto com event delegation para arrastar produtos entre lotes
 */

class DragDropHandler {
    constructor(workspace) {
        this.workspace = workspace;
        this.draggedElement = null;
        this.draggedData = null;
        this.isDragging = false; // Flag para evitar eventos duplicados
        this.isProcessingDrop = false; // Flag para evitar drops duplicados
        this.init();
    }

    init() {
        // Configurar event delegation global no documento
        this.setupGlobalDelegation();
        console.log('✅ Drag & Drop Handler inicializado com event delegation');
    }

    /**
     * 🎯 CONFIGURAÇÃO GLOBAL COM EVENT DELEGATION
     * Elimina necessidade de reconfigurar elementos individuais
     */
    setupGlobalDelegation() {
        // Dragstart - captura início do drag em qualquer produto
        document.addEventListener('dragstart', this.handleDragStart.bind(this), true);
        
        // Dragend - limpa estado após drag
        document.addEventListener('dragend', this.handleDragEnd.bind(this), true);
        
        // Dragover - permite drop em zonas válidas
        document.addEventListener('dragover', this.handleDragOver.bind(this), true);
        
        // Dragleave - remove visual feedback
        document.addEventListener('dragleave', this.handleDragLeave.bind(this), true);
        
        // Drop - processa o drop
        document.addEventListener('drop', this.handleDrop.bind(this), true);
        
        console.log('🎯 Event delegation configurado globalmente');
    }

    configurarDragDrop(numPedido) {
        // Apenas marcar elementos como draggable, sem adicionar listeners
        const workspaceElement = document.querySelector(`.workspace-montagem[data-pedido="${numPedido}"]`);
        if (!workspaceElement) {
            // Tentar sem o data-pedido como fallback
            const workspaceGenerico = document.querySelector('.workspace-montagem');
            if (workspaceGenerico) {
                console.warn(`⚠️ Usando workspace genérico, pedido ${numPedido} não encontrado`);
                this.marcarElementosDraggable(workspaceGenerico);
                return;
            }
            console.error(`❌ Workspace não encontrado para pedido ${numPedido}`);
            return;
        }

        console.log(`🔧 Marcando elementos draggable para pedido ${numPedido}`);
        this.marcarElementosDraggable(workspaceElement);
    }

    /**
     * 🎯 MARCAR ELEMENTOS COMO DRAGGABLE
     * Apenas adiciona atributos, sem listeners (delegation cuida disso)
     */
    marcarElementosDraggable(workspaceElement) {
        const produtos = workspaceElement.querySelectorAll('.produto-origem');
        console.log(`🎯 Marcando ${produtos.length} produtos como draggable`);

        produtos.forEach((tr, index) => {
            // Marcar como draggable
            tr.setAttribute('draggable', 'true');
            
            // Adicionar classe para styling
            tr.classList.add('draggable-produto');
            
            // Configurar visual de drag em toda a linha
            tr.style.cursor = 'move';
            tr.title = 'Clique e arraste para mover este produto';
            
            // Configurar handle visual se existir
            const handle = tr.querySelector('.drag-handle');
            if (handle) {
                handle.style.cursor = 'move';
            }
            
            // Validar dados necessários
            const codProduto = tr.dataset.produto;
            const qtdPedido = tr.dataset.qtdPedido;
            if (!codProduto || !qtdPedido) {
                console.warn(`⚠️ Produto ${index} sem dados necessários:`, { codProduto, qtdPedido });
                tr.setAttribute('draggable', 'false');
                tr.classList.add('drag-disabled');
            }
        });
        
        // Marcar drop zones
        const dropZones = workspaceElement.querySelectorAll('.lote-card, .lote-placeholder');
        dropZones.forEach(zone => {
            zone.classList.add('drop-zone');
            zone.setAttribute('data-drop-enabled', 'true');
        });
        
        console.log(`✅ ${dropZones.length} drop zones marcadas`);
    }

    /**
     * 🎯 HANDLERS COM EVENT DELEGATION
     */
    handleDragStart(e) {
        // Verificar se é um elemento draggable válido
        const produtoTr = e.target.closest('.produto-origem[draggable="true"]');
        if (!produtoTr) return;
        
        // Processar drag start sem restrição de handle
        this.processDragStart(e, produtoTr);
    }
    
    handleDragEnd(e) {
        const produtoTr = e.target.closest('.produto-origem');
        if (!produtoTr) return;
        
        this.processDragEnd(produtoTr);
    }
    
    handleDragOver(e) {
        const dropZone = e.target.closest('.drop-zone[data-drop-enabled="true"]');
        if (!dropZone || !this.draggedData) return;
        
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        dropZone.classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        const dropZone = e.target.closest('.drop-zone');
        if (!dropZone) return;
        
        // Verificar se realmente saiu da drop zone
        if (!dropZone.contains(e.relatedTarget)) {
            dropZone.classList.remove('drag-over');
        }
    }
    
    handleDrop(e) {
        const dropZone = e.target.closest('.drop-zone[data-drop-enabled="true"]');
        if (!dropZone || !this.draggedData) return;
        
        e.preventDefault();
        this.processDrop(e, dropZone);
    }

    /**
     * 🎯 PROCESSAR DRAG START
     */
    processDragStart(e, produtoTr) {
        // Evitar múltiplos drags simultâneos
        if (this.isDragging) {
            e.preventDefault();
            return;
        }
        
        console.log('🎯 Iniciando drag do produto');
        this.isDragging = true;
        
        const codProduto = produtoTr.dataset.produto;
        const qtdPedido = produtoTr.dataset.qtdPedido;
        
        if (!codProduto || !qtdPedido) {
            console.error('❌ Dados do produto incompletos', { codProduto, qtdPedido });
            e.preventDefault();
            this.mostrarFeedback('Erro: Dados do produto incompletos', 'error');
            return;
        }
        
        // Buscar quantidade editável atual
        const inputQtd = produtoTr.querySelector('.qtd-editavel');
        const qtdAtual = inputQtd ? parseInt(inputQtd.value) : parseInt(qtdPedido);
        
        if (isNaN(qtdAtual) || qtdAtual <= 0) {
            console.warn('⚠️ Quantidade inválida ou zero');
            e.preventDefault();
            this.mostrarFeedback('Não é possível arrastar produto com quantidade zero', 'warning');
            return;
        }
        
        // Armazenar dados do drag
        this.draggedElement = produtoTr;
        this.draggedData = {
            codProduto,
            qtdPedido: qtdAtual,
            nomeProduto: produtoTr.querySelector('.produto-info strong')?.textContent || codProduto
        };
        
        // Configurar dataTransfer
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', JSON.stringify(this.draggedData));
        
        // Visual feedback
        produtoTr.classList.add('dragging');
        produtoTr.style.opacity = '0.4';
        
        // Criar ghost image customizada
        const ghostImage = this.criarGhostImage(this.draggedData);
        if (ghostImage) {
            e.dataTransfer.setDragImage(ghostImage, 10, 10);
        }
        
        console.log('✅ Drag iniciado:', this.draggedData);
    }

    /**
     * 🎯 PROCESSAR DRAG END
     */
    processDragEnd(produtoTr) {
        console.log('🏁 Finalizando drag');
        
        // Limpar visual feedback
        produtoTr.classList.remove('dragging');
        produtoTr.style.opacity = '1';
        
        // Limpar todas as drop zones
        document.querySelectorAll('.drag-over').forEach(zone => {
            zone.classList.remove('drag-over');
        });
        
        // Limpar estado
        this.draggedElement = null;
        this.draggedData = null;
        this.isDragging = false; // Resetar flag
        
        // Remover ghost image se existir
        const ghost = document.getElementById('drag-ghost-image');
        if (ghost) ghost.remove();
    }

    /**
     * 🎯 CRIAR GHOST IMAGE CUSTOMIZADA
     */
    criarGhostImage(dados) {
        try {
            const ghost = document.createElement('div');
            ghost.id = 'drag-ghost-image';
            ghost.style.cssText = `
                position: absolute;
                top: -1000px;
                left: -1000px;
                background: white;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                font-family: inherit;
                z-index: 9999;
            `;
            
            ghost.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-box" style="color: #007bff;"></i>
                    <div>
                        <strong style="color: #333;">${dados.nomeProduto}</strong><br>
                        <small style="color: #666;">Qtd: ${dados.qtdPedido}</small>
                    </div>
                </div>
            `;
            
            document.body.appendChild(ghost);
            
            // Remover após pequeno delay
            setTimeout(() => ghost.remove(), 0);
            
            return ghost;
        } catch (error) {
            console.error('Erro ao criar ghost image:', error);
            return null;
        }
    }

    /**
     * 🎯 PROCESSAR DROP
     */
    async processDrop(e, dropZone) {
        // Evitar processamento duplicado de drops
        if (this.isProcessingDrop) {
            console.warn('⚠️ Drop já em processamento, ignorando...');
            return;
        }
        
        console.log('📦 Processando drop');
        this.isProcessingDrop = true;
        
        // Limpar visual feedback
        dropZone.classList.remove('drag-over');
        
        // Usar dados armazenados ao invés de dataTransfer (mais confiável)
        if (!this.draggedData) {
            console.warn('⚠️ Nenhum dado de drag encontrado');
            this.isProcessingDrop = false; // Resetar flag
            return;
        }
        
        try {
            const loteId = dropZone.dataset.loteId;
            
            // Drop no placeholder - criar novo lote
            if (dropZone.classList.contains('lote-placeholder')) {
                await this.processarDropNoPlaceholder(dropZone);
            }
            // Drop em lote existente
            else if (loteId && loteId !== 'placeholder') {
                await this.processarDropNoLote(loteId);
            }
            else {
                console.warn('⚠️ Drop zone inválida');
                this.mostrarFeedback('Área de drop inválida', 'error');
            }
            
        } catch (error) {
            console.error('❌ Erro no drop:', error);
            this.mostrarFeedback(`Erro ao adicionar produto: ${error.message}`, 'error');
        } finally {
            // Sempre resetar a flag no final
            this.isProcessingDrop = false;
        }
    }
    
    /**
     * 🎯 PROCESSAR DROP NO PLACEHOLDER
     */
    async processarDropNoPlaceholder(dropZone) {
        console.log('🎯 Criando novo lote via drop');
        
        const workspaceElement = dropZone.closest('.workspace-montagem');
        const numPedido = workspaceElement?.dataset.pedido || this.workspace.obterNumeroPedido();
        
        if (!numPedido) {
            throw new Error('Número do pedido não identificado');
        }
        
        // Gerar novo lote
        const novoLoteId = this.workspace.gerarNovoLoteId();
        console.log(`✨ Criando lote ${novoLoteId}`);
        
        // Criar lote e adicionar produto
        await this.workspace.criarLote(numPedido, novoLoteId);
        await this.workspace.adicionarProdutoNoLote(novoLoteId, this.draggedData);
        
        // Marcar novo card como drop zone
        setTimeout(() => {
            const newCard = document.querySelector(`[data-lote-id="${novoLoteId}"]`);
            if (newCard) {
                newCard.classList.add('drop-zone');
                newCard.setAttribute('data-drop-enabled', 'true');
                this.mostrarFeedback('Novo lote criado com sucesso!', 'success');
            }
        }, 100);
    }
    
    /**
     * 🎯 PROCESSAR DROP EM LOTE EXISTENTE
     */
    async processarDropNoLote(loteId) {
        console.log(`📦 Adicionando ao lote ${loteId}`);
        
        await this.workspace.adicionarProdutoNoLote(loteId, this.draggedData);
        this.mostrarFeedback('Produto adicionado ao lote!', 'success');
    }

    /**
     * 🎯 MOSTRAR FEEDBACK VISUAL
     */
    mostrarFeedback(mensagem, tipo = 'info') {
        // Criar toast notification
        const toast = document.createElement('div');
        toast.className = `toast-feedback toast-${tipo}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${tipo === 'success' ? '#28a745' : tipo === 'error' ? '#dc3545' : '#ffc107'};
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        toast.textContent = mensagem;
        document.body.appendChild(toast);
        
        // Remover após 3 segundos
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    /**
     * 🎯 RECONFIGURAR APÓS MUDANÇAS DINÂMICAS
     */
    reconfigurarTudo(numPedido) {
        console.log(`🔄 Reconfigurando drag & drop para pedido ${numPedido}`);
        this.configurarDragDrop(numPedido);
    }
}

// Disponibilizar globalmente
window.DragDropHandler = DragDropHandler;

// Função global para debug do drag & drop
window.debugDragDrop = function (numPedido) {
    const workspace = window.workspace;
    if (!workspace || !workspace.dragDropHandler) {
        console.error('❌ Workspace ou DragDropHandler não encontrado');
        return;
    }

    console.log('🔍 DEBUG DRAG & DROP');
    console.log('- Workspace:', !!workspace);
    console.log('- DragDropHandler:', !!workspace.dragDropHandler);

    if (numPedido) {
        console.log(`- Reconfigurando para pedido: ${numPedido}`);
        workspace.dragDropHandler.reconfigurarTudo(numPedido);
    }
};

// CSS para animações do toast
if (!document.getElementById('drag-drop-animations')) {
    const style = document.createElement('style');
    style.id = 'drag-drop-animations';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}