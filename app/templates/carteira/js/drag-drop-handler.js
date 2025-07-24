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
        if (!workspaceElement) {
            console.error(`❌ Workspace não encontrado para pedido ${numPedido}`);
            return;
        }

        console.log(`🔧 Configurando drag & drop para pedido ${numPedido}`);

        // Configurar drag nos produtos
        this.configurarDragProducts(workspaceElement);

        // Configurar drop nos lotes
        this.configurarDropZones(workspaceElement);
    }

    configurarDragProducts(workspaceElement) {
        const produtos = workspaceElement.querySelectorAll('.produto-origem');
        console.log(`🎯 Configurando ${produtos.length} produtos para drag`);
        
        produtos.forEach((row, index) => {
            // Remover event listeners existentes para evitar duplicação
            row.removeEventListener('dragstart', this.onDragStart);
            row.removeEventListener('dragend', this.onDragEnd);
            
            // Adicionar novos event listeners
            row.addEventListener('dragstart', (e) => this.onDragStart(e));
            row.addEventListener('dragend', (e) => this.onDragEnd(e));
            
            // Verificar se tem dados necessários
            const codProduto = row.dataset.produto;
            const qtdPedido = row.dataset.qtdPedido;
            
            if (!codProduto || !qtdPedido) {
                console.warn(`⚠️ Produto ${index} sem dados necessários:`, { codProduto, qtdPedido });
            }
        });
    }

    configurarDropZones(workspaceElement) {
        const dropZones = workspaceElement.querySelectorAll('.lote-card, .lote-placeholder');
        console.log(`🎯 Configurando ${dropZones.length} drop zones`);
        
        dropZones.forEach((card, index) => {
            // Remover event listeners existentes para evitar duplicação
            card.removeEventListener('dragover', this.onDragOver);
            card.removeEventListener('dragleave', this.onDragLeave);
            card.removeEventListener('drop', this.onDrop);
            
            // Adicionar novos event listeners
            card.addEventListener('dragover', (e) => this.onDragOver(e));
            card.addEventListener('dragleave', (e) => this.onDragLeave(e));
            card.addEventListener('drop', (e) => this.onDrop(e));
            
            // Log para debug
            const isPlaceholder = card.classList.contains('lote-placeholder');
            const loteId = card.dataset.loteId;
            console.log(`  - Drop zone ${index}: ${isPlaceholder ? 'PLACEHOLDER' : `Lote ${loteId}`}`);
        });
    }

    onDragStart(e) {
        console.log('🎯 onDragStart chamado!', e.currentTarget);
        
        const row = e.currentTarget;
        const codProduto = row.dataset.produto;
        const qtdPedido = row.dataset.qtdPedido;
        
        console.log('📋 Dados do produto para drag:', { codProduto, qtdPedido });
        
        if (!codProduto || !qtdPedido) {
            console.error('❌ Dados do produto incompletos', { codProduto, qtdPedido });
            e.preventDefault();
            alert('❌ Erro: Dados do produto incompletos');
            return;
        }
        
        // Buscar quantidade editável atual
        const inputQtd = row.querySelector('.qtd-editavel');
        const qtdAtual = inputQtd ? parseInt(inputQtd.value) : parseInt(qtdPedido);
        
        console.log('📊 Quantidade para drag:', { inputValue: inputQtd?.value, qtdAtual, qtdPedido });
        
        if (isNaN(qtdAtual) || qtdAtual <= 0) {
            console.warn('⚠️ Quantidade inválida ou zero');
            e.preventDefault();
            alert('⚠️ Não é possível arrastar produto com quantidade zero ou inválida');
            return;
        }
        
        const dadosDrag = {
            codProduto,
            qtdPedido: qtdAtual
        };
        
        e.dataTransfer.setData('text/plain', JSON.stringify(dadosDrag));
        e.dataTransfer.effectAllowed = 'move';
        
        row.classList.add('dragging');
        console.log(`✅ Drag iniciado com sucesso:`, dadosDrag);
    }

    onDragEnd(e) {
        e.currentTarget.classList.remove('dragging');
    }

    onDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = 'move'; // Mostra cursor de permitido
        e.currentTarget.classList.add('drag-over');
    }

    onDragLeave(e) {
        // Só remove se realmente saiu da zona (não de um elemento filho)
        if (!e.currentTarget.contains(e.relatedTarget)) {
            e.currentTarget.classList.remove('drag-over');
        }
    }

    async onDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('drag-over');
        
        console.log('📦 Drop detectado!', {
            target: e.currentTarget.className,
            isPlaceholder: e.currentTarget.classList.contains('lote-placeholder'),
            loteId: e.currentTarget.dataset.loteId
        });
        
        try {
            const dataTransfer = e.dataTransfer.getData('text/plain');
            if (!dataTransfer) {
                console.error('❌ Dados do drag não encontrados');
                return;
            }
            
            const data = JSON.parse(dataTransfer);
            console.log('📋 Dados do produto:', data);
            
            const loteId = e.currentTarget.dataset.loteId;
            
            // Se dropou no placeholder, criar novo lote automaticamente
            if (e.currentTarget.classList.contains('lote-placeholder')) {
                console.log('🎯 Drop no placeholder - criando novo lote');
                
                const workspaceElement = e.currentTarget.closest('.workspace-montagem');
                const numPedido = workspaceElement ? workspaceElement.dataset.pedido : null;
                
                if (!numPedido) {
                    console.error('❌ Número do pedido não encontrado');
                    alert('❌ Erro: Não foi possível identificar o pedido');
                    return;
                }
                
                // Gerar novo lote e adicionar produto
                const novoLoteId = this.workspace.gerarNovoLoteId();
                console.log(`✨ Criando lote ${novoLoteId} para pedido ${numPedido}`);
                
                // Criar lote primeiro
                await this.workspace.criarLote(numPedido, novoLoteId);
                
                // Depois adicionar produto
                await this.workspace.adicionarProdutoNoLote(novoLoteId, {
                    codProduto: data.codProduto,
                    qtdPedido: data.qtdPedido
                });
                
                // Reconfigurar drag & drop após criar novo lote
                setTimeout(() => {
                    this.reconfigurarTudo(numPedido);
                }, 100);
                
            } else if (loteId) {
                console.log(`📦 Drop no lote existente: ${loteId}`);
                await this.workspace.adicionarProdutoNoLote(loteId, {
                    codProduto: data.codProduto,
                    qtdPedido: data.qtdPedido
                });
            } else {
                console.warn('⚠️ Drop zone sem lote_id definido');
                alert('⚠️ Erro: Drop zone não configurada corretamente');
            }
            
        } catch (error) {
            console.error('❌ Erro no drop:', error);
            alert(`❌ Erro ao adicionar produto: ${error.message}`);
        }
    }

    // Reconfigurar drop zones após criar novos lotes
    reconfigurarDropZone(loteCard) {
        if (!loteCard) {
            console.warn('⚠️ Tentativa de reconfigurar drop zone em elemento nulo');
            return;
        }
        
        console.log('🔧 Reconfigurando drop zone para:', loteCard.dataset.loteId || 'elemento sem ID');
        
        // Remover event listeners existentes
        loteCard.removeEventListener('dragover', this.onDragOver);
        loteCard.removeEventListener('dragleave', this.onDragLeave);
        loteCard.removeEventListener('drop', this.onDrop);
        
        // Adicionar novos event listeners
        loteCard.addEventListener('dragover', (e) => this.onDragOver(e));
        loteCard.addEventListener('dragleave', (e) => this.onDragLeave(e));
        loteCard.addEventListener('drop', (e) => this.onDrop(e));
    }

    // Função para reconfigurar tudo após mudanças dinâmicas
    reconfigurarTudo(numPedido) {
        console.log(`🔄 Reconfigurando todo o drag & drop para pedido ${numPedido}`);
        this.configurarDragDrop(numPedido);
    }
}

// Disponibilizar globalmente
window.DragDropHandler = DragDropHandler;

// Função global para debug do drag & drop
window.debugDragDrop = function(numPedido) {
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