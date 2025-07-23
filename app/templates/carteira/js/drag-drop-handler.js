/**
 * 🎯 DRAG & DROP HANDLER
 * Gerencia todas as funcionalidades de arrastar e soltar produtos entre lotes
 */

class DragDropHandler {
    constructor(workspace) {
        this.workspace = workspace;
        this.init();
    }

    init() {
        console.log('✅ Drag & Drop Handler inicializado');
    }

    configurarDragDrop(numPedido) {
        const workspaceElement = document.querySelector(`[data-pedido="${numPedido}"]`);
        if (!workspaceElement) return;

        // Configurar drag nos produtos
        workspaceElement.querySelectorAll('.produto-origem').forEach(row => {
            row.addEventListener('dragstart', (e) => this.onDragStart(e));
            row.addEventListener('dragend', (e) => this.onDragEnd(e));
        });

        // Configurar drop nos lotes
        this.configurarDropZones(workspaceElement);
    }

    configurarDropZones(workspaceElement) {
        workspaceElement.querySelectorAll('.lote-card, .lote-placeholder').forEach(card => {
            card.addEventListener('dragover', (e) => this.onDragOver(e));
            card.addEventListener('drop', (e) => this.onDrop(e));
        });
    }

    onDragStart(e) {
        const row = e.currentTarget;
        const codProduto = row.dataset.produto;
        const qtdPedido = row.dataset.qtdPedido;
        
        e.dataTransfer.setData('text/plain', JSON.stringify({
            codProduto,
            qtdPedido: parseFloat(qtdPedido)
        }));
        
        row.classList.add('dragging');
        console.log(`🔄 Iniciando drag do produto ${codProduto}`);
    }

    onDragEnd(e) {
        e.currentTarget.classList.remove('dragging');
    }

    onDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
    }

    onDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        
        try {
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const loteId = e.currentTarget.dataset.loteId;
            
            // Se dropou no placeholder, criar novo lote
            if (e.currentTarget.classList.contains('lote-placeholder')) {
                const numPedido = e.currentTarget.closest('.workspace-montagem').dataset.pedido;
                const novoLoteId = this.workspace.gerarNovoLoteId();
                this.workspace.criarLote(numPedido, novoLoteId);
                this.workspace.adicionarProdutoNoLote(novoLoteId, data);
            } else if (loteId) {
                this.workspace.adicionarProdutoNoLote(loteId, data);
            }
            
        } catch (error) {
            console.error('❌ Erro no drop:', error);
        }
    }

    // Reconfigurar drop zones após criar novos lotes
    reconfigurarDropZone(loteCard) {
        loteCard.addEventListener('dragover', (e) => this.onDragOver(e));
        loteCard.addEventListener('drop', (e) => this.onDrop(e));
    }
}

// Disponibilizar globalmente
window.DragDropHandler = DragDropHandler;