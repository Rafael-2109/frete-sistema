/**
 * Sistema de Navegação entre Modais com Breadcrumb
 * Gerencia o fluxo de navegação entre diferentes modais mantendo histórico
 */

class ModalNavigationManager {
    constructor() {
        this.navigationStack = [];
        this.modals = new Map();
        this.init();
    }
    
    init() {
        console.log('🧭 Sistema de navegação entre modais inicializado');
        this.createBreadcrumbContainer();
        this.injectStyles();
    }
    
    /**
     * Injeta estilos CSS necessários
     */
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Ajustar modais quando breadcrumb está visível */
            .modal-breadcrumb-active .modal-dialog {
                margin-top: 70px !important;
            }
            
            /* Garantir que o breadcrumb fique acima dos modais */
            #modal-breadcrumb-container {
                z-index: 1055 !important;
            }
            
            /* Ajustar z-index dos modais para ficarem abaixo do breadcrumb */
            .modal {
                z-index: 1050 !important;
            }
            
            .modal-backdrop {
                z-index: 1049 !important;
            }
            
            /* Melhorar visual do breadcrumb */
            .breadcrumb-item {
                transition: all 0.3s ease;
                padding: 4px 8px;
                border-radius: 4px;
            }
            
            .breadcrumb-item:hover:not(.active) {
                background-color: rgba(108, 117, 125, 0.15);
                color: var(--bs-body-color);
            }

            .breadcrumb-item.active {
                background-color: rgba(108, 117, 125, 0.15);
                border-radius: 4px;
            }
        `;
        document.head.appendChild(style);
    }
    
    /**
     * Cria container para breadcrumb fixo no topo
     */
    createBreadcrumbContainer() {
        if (document.getElementById('modal-breadcrumb-container')) return;
        
        const container = document.createElement('div');
        container.id = 'modal-breadcrumb-container';
        container.className = 'modal-breadcrumb-container';
        container.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: var(--bs-secondary-bg);
            border-bottom: 2px solid var(--bs-border-color);
            padding: 10px 20px;
            z-index: 1055;
            display: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            backdrop-filter: blur(10px);
        `;
        
        document.body.appendChild(container);
    }
    
    /**
     * Adiciona um modal à pilha de navegação
     */
    pushModal(modalId, title, data = {}) {
        // Não fazer verificação de duplicatas - permitir múltiplas instâncias
        // Exemplo: Pedido 1 -> Cardex -> Pedido 2 é válido
        
        console.log(`🧭 Push modal: ${title} (${modalId}). Stack atual:`, this.navigationStack.map(item => item.title));
        
        this.navigationStack.push({
            id: modalId,
            title: title,
            data: data,
            timestamp: Date.now()
        });
        
        this.updateBreadcrumb();
        this.showBreadcrumb();
        
        console.log(`🧭 Stack após push:`, this.navigationStack.map(item => item.title));
    }
    
    /**
     * Remove o modal atual e volta ao anterior
     */
    popModal() {
        if (this.navigationStack.length > 0) {
            const modalRemovido = this.navigationStack.pop();
            console.log(`🧭 Pop modal: ${modalRemovido.title}. Stack restante:`, this.navigationStack.map(item => item.title));
            
            // Atualizar breadcrumb
            this.updateBreadcrumb();
            
            // Se não houver mais modais, esconder breadcrumb
            if (this.navigationStack.length === 0) {
                this.hideBreadcrumb();
                
                // Limpar backdrops restantes
                document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                    backdrop.remove();
                });
                
                // Remover classe modal-open do body
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('padding-right');
            }
        }
    }
    
    /**
     * Volta para um modal específico na pilha
     */
    navigateToModal(index) {
        if (index < 0 || index >= this.navigationStack.length) return;
        
        // Se clicar no item atual, não fazer nada
        if (index === this.navigationStack.length - 1) return;
        
        console.log(`🧭 Navegando para modal no índice ${index} (${this.navigationStack[index].title})`);
        console.log(`🧭 Stack antes:`, this.navigationStack.map((item, i) => `${i}: ${item.title} (${item.id})`));
        
        // Coletar todos os modais que devem ser fechados (todos após o índice selecionado)
        const modaisParaFechar = [];
        for (let i = this.navigationStack.length - 1; i > index; i--) {
            modaisParaFechar.push({
                id: this.navigationStack[i].id,
                index: i,
                title: this.navigationStack[i].title
            });
        }
        
        console.log(`🧭 Vamos fechar ${modaisParaFechar.length} modal(is):`, modaisParaFechar.map(m => m.title));
        
        // Fechar TODOS os modais visíveis que não estão na pilha até o índice selecionado
        const todosModais = document.querySelectorAll('.modal.show');
        todosModais.forEach(modal => {
            // Verificar se este modal deve permanecer (está na pilha até o índice)
            let devePermanecer = false;
            for (let i = 0; i <= index; i++) {
                if (modal.id === this.navigationStack[i].id) {
                    devePermanecer = true;
                    break;
                }
            }
            
            if (!devePermanecer) {
                console.log(`🧭 Fechando modal: ${modal.id}`);
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    modal._skipNavigation = true;
                    bsModal.hide();
                }
                // Remover do DOM
                setTimeout(() => {
                    if (modal.parentNode) {
                        modal.remove();
                    }
                }, 150);
            }
        });
        
        // Atualizar a pilha removendo todos após o índice
        this.navigationStack = this.navigationStack.slice(0, index + 1);
        
        // Limpar TODOS os backdrops e deixar apenas um se necessário
        setTimeout(() => {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            console.log(`🧭 Encontrados ${backdrops.length} backdrop(s)`);
            
            // Remover todos os backdrops
            backdrops.forEach(backdrop => backdrop.remove());
            
            // Se ainda houver modal visível, adicionar um backdrop
            const modalVisivel = document.querySelector('.modal.show');
            if (modalVisivel && this.navigationStack.length > 0) {
                const novoBackdrop = document.createElement('div');
                novoBackdrop.className = 'modal-backdrop fade show';
                document.body.appendChild(novoBackdrop);
            }
        }, 300);
        
        // Atualizar breadcrumb
        this.updateBreadcrumb();
        
        console.log(`🧭 Navegação concluída. Stack final:`, this.navigationStack.map((item, i) => `${i}: ${item.title}`));
    }
    
    /**
     * Atualiza o breadcrumb visual
     */
    updateBreadcrumb() {
        const container = document.getElementById('modal-breadcrumb-container');
        if (!container) return;
        
        const breadcrumb = this.navigationStack.map((item, index) => {
            const isLast = index === this.navigationStack.length - 1;
            const icon = this.getIconForModal(item.id);
            
            return `
                <span class="breadcrumb-item ${isLast ? 'active fw-bold' : ''}" 
                      data-index="${index}"
                      style="cursor: ${isLast ? 'default' : 'pointer'}; ${isLast ? 'font-weight: 600;' : ''}">
                    <i class="${icon} me-1"></i>
                    ${item.title}
                </span>
                ${!isLast ? '<i class="fas fa-chevron-right mx-2 text-muted"></i>' : ''}
            `;
        }).join('');
        
        container.innerHTML = `
            <div class="d-flex align-items-center">
                <button class="btn btn-sm btn-outline-secondary me-3" onclick="modalNav.clearNavigation()" title="Fechar todos os modais">
                    <i class="fas fa-times"></i>
                </button>
                <div class="breadcrumb-trail d-flex align-items-center">
                    ${breadcrumb}
                </div>
            </div>
        `;
        
        // Adicionar listeners aos itens do breadcrumb
        container.querySelectorAll('.breadcrumb-item:not(.active)').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.navigateToModal(index);
            });
        });
    }
    
    /**
     * Retorna ícone apropriado para cada tipo de modal
     */
    getIconForModal(modalId) {
        const icons = {
            'modalRuptura': 'fas fa-exclamation-triangle',
            'modalCardex': 'fas fa-chart-line',
            'modalCardexExpandido': 'fas fa-table',
            'modalPedidoDetalhes': 'fas fa-box',
            'modalWorkspace': 'fas fa-boxes'
        };
        return icons[modalId] || 'fas fa-window-maximize';
    }
    
    /**
     * Mostra o breadcrumb
     */
    showBreadcrumb() {
        const container = document.getElementById('modal-breadcrumb-container');
        if (container) {
            container.style.display = 'block';
            
            // Adicionar classe ao body para aplicar estilos
            document.body.classList.add('modal-breadcrumb-active');
            
            // Forçar reposicionamento dos modais abertos
            setTimeout(() => {
                const modals = document.querySelectorAll('.modal.show .modal-dialog');
                modals.forEach(modal => {
                    modal.style.marginTop = '70px';
                });
            }, 50);
        }
    }
    
    /**
     * Esconde o breadcrumb
     */
    hideBreadcrumb() {
        const container = document.getElementById('modal-breadcrumb-container');
        if (container) {
            container.style.display = 'none';
            
            // Remover classe do body
            document.body.classList.remove('modal-breadcrumb-active');
            
            // Restaurar margem dos modais
            const modals = document.querySelectorAll('.modal-dialog');
            modals.forEach(modal => {
                modal.style.marginTop = '';
            });
        }
    }
    
    /**
     * Limpa toda a navegação
     */
    clearNavigation() {
        // Fechar todos os modais
        this.navigationStack.forEach(item => {
            this.closeModalOnly(item.id);
        });
        
        this.navigationStack = [];
        this.hideBreadcrumb();
        
        // Limpar todos os backdrops
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.remove();
        });
        
        // Remover classe de body se houver
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('padding-right');
    }
    
    /**
     * Fecha um modal específico
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
            // Remover modal do DOM após animação
            setTimeout(() => {
                if (modal && modal.parentNode) {
                    modal.remove();
                }
            }, 300);
        }
    }
    
    /**
     * Fecha um modal sem remover do DOM (para navegação)
     */
    closeModalOnly(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                // Remover listener do evento hidden para evitar remoção automática
                modal.removeEventListener('hidden.bs.modal', null);
                bsModal.hide();
            }
            // Remover modal do DOM imediatamente
            if (modal.parentNode) {
                modal.remove();
            }
        }
        
        // Limpar backdrops extras se houver
        const backdrops = document.querySelectorAll('.modal-backdrop');
        if (backdrops.length > 1) {
            for (let i = 1; i < backdrops.length; i++) {
                backdrops[i].remove();
            }
        }
    }
    
    /**
     * Reabre um modal com dados salvos
     */
    reopenModal(modalId, data) {
        // Implementação específica para cada tipo de modal
        switch(modalId) {
            case 'modalRuptura':
                if (window.rupturaManager) {
                    window.rupturaManager.mostrarModalRuptura(data);
                }
                break;
            case 'modalCardex':
                if (window.modalCardex) {
                    window.modalCardex.abrirCardex(data.codProduto, data.dadosProdutos);
                }
                break;
            case 'modalCardexExpandido':
                this.abrirCardexExpandido(data);
                break;
            case 'modalPedidoDetalhes':
                if (window.pedidoDetalhes) {
                    window.pedidoDetalhes.abrirPedidoDetalhes(data.numPedido);
                } else {
                    // Carregar script se não estiver carregado
                    const script = document.createElement('script');
                    script.src = '/static/carteira/js/modal-pedido-detalhes.js';
                    script.onload = () => {
                        if (window.pedidoDetalhes) {
                            window.pedidoDetalhes.abrirPedidoDetalhes(data.numPedido);
                        }
                    };
                    document.head.appendChild(script);
                }
                break;
            default:
                console.warn(`Modal ${modalId} não tem handler de reabertura`);
        }
    }
    
    /**
     * Abre modal de Cardex Expandido com detalhes de saídas
     */
    abrirCardexExpandido(data) {
        // Será implementado na próxima etapa
        console.log('Abrindo Cardex Expandido', data);
    }
    
    /**
     * Abre modal de detalhes do pedido
     */
    abrirPedidoDetalhes(data) {
        // Será implementado na próxima etapa
        console.log('Abrindo Detalhes do Pedido', data);
    }
}

// Instanciar globalmente
window.modalNav = new ModalNavigationManager();