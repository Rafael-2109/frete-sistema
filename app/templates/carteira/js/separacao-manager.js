/**
 * 🎯 SEPARAÇÃO MANAGER - Refatorado com Parciais HTML
 * Usa o servidor como fonte única de verdade
 * Atualiza apenas os trechos necessários do DOM
 */

class SeparacaoManager {
    constructor() {
        this.expandedPedidos = new Set();
        this.currentFilters = new URLSearchParams(window.location.search);
        this.processingRequests = new Set(); // Prevenir duplo clique
        this.init();
    }

    init() {
        console.log('✅ Separação Manager inicializado');
        this.restoreExpandedState();
        this.setupEventDelegation();
    }
    
    /**
     * 🎯 CONFIGURAR DELEGAÇÃO DE EVENTOS
     * Evita perder listeners quando o DOM é atualizado
     */
    setupEventDelegation() {
        // Delegação para botões de gerar separação
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-gerar-separacao');
            if (!btn) return;
            e.preventDefault();
            
            const numPedido = btn.dataset.pedido || btn.closest('[data-pedido]')?.dataset.pedido;
            if (!numPedido) return;
            
            // Prevenir duplo clique
            if (this.processingRequests.has(numPedido)) return;
            
            this.criarSeparacaoCompleta(numPedido);
        });
        
        // Delegação para transformar lote
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-transformar-lote');
            if (!btn) return;
            e.preventDefault();
            
            const loteId = btn.dataset.loteId;
            if (!loteId) return;
            
            if (this.processingRequests.has(loteId)) return;
            
            this.transformarLoteEmSeparacao(loteId);
        });
        
        // Delegação para excluir separação
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-excluir-separacao');
            if (!btn) return;
            e.preventDefault();
            
            const separacaoId = btn.dataset.separacaoId;
            const numPedido = btn.dataset.pedido;
            
            if (!separacaoId) return;
            
            this.excluirSeparacao(separacaoId, numPedido);
        });
        
        // Delegação para excluir pré-separação
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-excluir-pre-separacao');
            if (!btn) return;
            e.preventDefault();
            
            const loteId = btn.dataset.loteId;
            const numPedido = btn.dataset.pedido;
            
            if (!loteId) return;
            
            this.excluirPreSeparacao(loteId, numPedido);
        });
    }

    /**
     * 🔄 APLICAR PARCIAIS HTML RETORNADOS DO SERVIDOR
     * Esta é a função central que atualiza o DOM com os parciais
     */
    async applyTargets(data) {
        if (!data?.targets) return;
        
        for (const [selector, html] of Object.entries(data.targets)) {
            const element = document.querySelector(selector);
            if (element) {
                // Salvar estado de expansão se for um collapse
                const wasExpanded = element.classList?.contains('show');
                
                // Substituir HTML
                element.outerHTML = html;
                
                // Restaurar estado de expansão
                if (wasExpanded) {
                    const newElement = document.querySelector(selector);
                    if (newElement?.classList?.contains('collapse')) {
                        newElement.classList.add('show');
                    }
                }
                
                // Adicionar animação de atualização
                const updatedElement = document.querySelector(selector);
                if (updatedElement) {
                    updatedElement.classList.add('update-animation');
                    setTimeout(() => {
                        updatedElement.classList.remove('update-animation');
                    }, 1000);
                }
            }
        }
    }

    /**
     * 🎯 CRIAR SEPARAÇÃO COMPLETA
     */
    async criarSeparacaoCompleta(numPedido) {
        console.log(`📦 Criar separação completa para pedido ${numPedido}`);
        
        // Prevenir duplo processamento
        if (this.processingRequests.has(numPedido)) {
            console.log('⚠️ Requisição já em andamento para', numPedido);
            return;
        }
        
        const dataExpedicao = await this.solicitarDataExpedicao();
        if (!dataExpedicao) return;
        
        // Adicionar à lista de processamento
        this.processingRequests.add(numPedido);
        
        const botao = document.querySelector(`[data-pedido="${numPedido}"] .btn-gerar-separacao`);
        
        try {
            // Loading local no botão
            if (botao) {
                botao.disabled = true;
                botao.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processando...';
            }
            
            const response = await fetch(`/carteira/api/pedido/${numPedido}/gerar-separacao-completa`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/html',  // IMPORTANTE: Solicitar HTML para receber targets
                    'X-CSRFToken': this.getCSRFToken()  // Adicionar CSRF token
                },
                body: JSON.stringify({
                    expedicao: dataExpedicao.expedicao,
                    agendamento: dataExpedicao.agendamento,
                    protocolo: dataExpedicao.protocolo
                })
            });
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                // Aplicar parciais HTML retornados
                await this.applyTargets(data);
                
                // Atualizar contadores globais
                if (data.contadores) {
                    this.atualizarContadores(data.contadores);
                }
                
                // Feedback de sucesso
                this.mostrarSucesso(data.message || 'Separação criada com sucesso!');
            } else {
                this.mostrarErro(data.error || 'Erro ao criar separação');
                
                // Restaurar botão em caso de erro
                if (botao) {
                    botao.disabled = false;
                    botao.innerHTML = '<i class="fas fa-truck-loading me-1"></i>Gerar Separação';
                }
            }
        } catch (error) {
            console.error('Erro ao criar separação:', error);
            this.mostrarErro('Erro de comunicação com o servidor');
            
            // Restaurar botão
            if (botao) {
                botao.disabled = false;
                botao.innerHTML = '<i class="fas fa-truck-loading me-1"></i>Gerar Separação';
            }
        } finally {
            // Remover da lista de processamento
            this.processingRequests.delete(numPedido);
        }
    }

    /**
     * 🔄 TRANSFORMAR PRÉ-SEPARAÇÃO EM SEPARAÇÃO
     */
    async transformarLoteEmSeparacao(loteId) {
        console.log(`🔄 Transformar lote ${loteId} em separação`);
        
        const botao = document.querySelector(`[data-lote-id="${loteId}"] .btn-transformar`);
        
        try {
            // Loading local no botão
            if (botao) {
                botao.disabled = true;
                botao.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Transformando...';
            }
            
            const response = await fetch(`/carteira/api/lote/${loteId}/transformar-separacao`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/html',  // Solicitar parciais HTML
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                // Aplicar parciais HTML
                await this.applyTargets(data);
                
                // Atualizar contadores
                if (data.contadores) {
                    this.atualizarContadores(data.contadores);
                }
                
                this.mostrarSucesso(data.message || 'Transformado com sucesso!');
            } else {
                this.mostrarErro(data.error || 'Erro ao transformar');
                
                // Restaurar botão
                if (botao) {
                    botao.disabled = false;
                    botao.innerHTML = '<i class="fas fa-exchange-alt me-1"></i>Transformar';
                }
            }
        } catch (error) {
            console.error('Erro:', error);
            this.mostrarErro('Erro de comunicação');
            
            if (botao) {
                botao.disabled = false;
                botao.innerHTML = '<i class="fas fa-exchange-alt me-1"></i>Transformar';
            }
        }
    }

    /**
     * 🗑️ EXCLUIR SEPARAÇÃO
     */
    async excluirSeparacao(separacaoId, numPedido) {
        if (!await this.confirmarAcao('Excluir Separação', 'Esta ação não pode ser desfeita.')) {
            return;
        }
        
        console.log(`🗑️ Excluindo separação ${separacaoId} do pedido ${numPedido}`);
        
        const card = document.querySelector(`[data-separacao-id="${separacaoId}"]`);
        
        try {
            // Adicionar classe de exclusão
            if (card) {
                card.classList.add('deleting');
            }
            
            const response = await fetch(`/carteira/api/separacao/${separacaoId}/excluir`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/html',  // Solicitar parciais HTML
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                // Aplicar parciais (servidor retorna HTML atualizado)
                await this.applyTargets(data);
                
                // Atualizar contadores
                if (data.contadores) {
                    this.atualizarContadores(data.contadores);
                }
                
                this.mostrarSucesso('Separação excluída');
            } else {
                // Remover classe de exclusão em caso de erro
                if (card) {
                    card.classList.remove('deleting');
                }
                this.mostrarErro(data.error || 'Erro ao excluir');
            }
        } catch (error) {
            console.error('Erro:', error);
            if (card) {
                card.classList.remove('deleting');
            }
            this.mostrarErro('Erro de comunicação');
        }
    }

    /**
     * 🗑️ EXCLUIR PRÉ-SEPARAÇÃO
     */
    async excluirPreSeparacao(loteId, numPedido) {
        if (!await this.confirmarAcao('Excluir Pré-Separação', 'Esta ação não pode ser desfeita.')) {
            return;
        }
        
        console.log(`🗑️ Excluindo pré-separação ${loteId} do pedido ${numPedido}`);
        
        const card = document.querySelector(`[data-lote-id="${loteId}"]`);
        
        try {
            if (card) {
                card.classList.add('deleting');
            }
            
            const response = await fetch(`/carteira/api/pre-separacao/${loteId}/excluir`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/html',  // Solicitar parciais HTML
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                await this.applyTargets(data);
                
                if (data.contadores) {
                    this.atualizarContadores(data.contadores);
                }
                
                this.mostrarSucesso('Pré-separação excluída');
            } else {
                if (card) {
                    card.classList.remove('deleting');
                }
                this.mostrarErro(data.error || 'Erro ao excluir');
            }
        } catch (error) {
            console.error('Erro:', error);
            if (card) {
                card.classList.remove('deleting');
            }
            this.mostrarErro('Erro de comunicação');
        }
    }

    /**
     * 📊 ATUALIZAR CONTADORES (valores do servidor)
     */
    atualizarContadores(contadores) {
        if (!contadores) return;
        
        // Atualizar cada contador com o valor real do servidor
        for (const [id, valor] of Object.entries(contadores)) {
            const elemento = document.getElementById(id);
            if (elemento) {
                const valorAnterior = elemento.textContent;
                elemento.textContent = valor;
                
                // Animação apenas se o valor mudou
                if (valorAnterior !== String(valor)) {
                    elemento.classList.add('pulse-animation');
                    setTimeout(() => {
                        elemento.classList.remove('pulse-animation');
                    }, 1000);
                }
            }
        }
    }

    /**
     * 🔄 BUSCAR CONTADORES DO SERVIDOR
     */
    async refreshContadores() {
        try {
            const response = await fetch('/carteira/api/contadores');
            const data = await response.json();
            
            if (data.ok && data.contadores) {
                this.atualizarContadores(data.contadores);
            }
        } catch (error) {
            console.error('Erro ao buscar contadores:', error);
        }
    }

    /**
     * 📅 SOLICITAR DATA DE EXPEDIÇÃO
     */
    async solicitarDataExpedicao() {
        return new Promise((resolve) => {
            // Se tem SweetAlert, usar modal bonito
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Data de Expedição',
                    html: `
                        <div class="mb-3">
                            <label class="form-label">Data de Expedição *</label>
                            <input type="date" id="swal-expedicao" class="form-control" 
                                   value="${new Date().toISOString().split('T')[0]}" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Agendamento (opcional)</label>
                            <input type="date" id="swal-agendamento" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Protocolo (opcional)</label>
                            <input type="text" id="swal-protocolo" class="form-control">
                        </div>
                    `,
                    showCancelButton: true,
                    confirmButtonText: 'Confirmar',
                    cancelButtonText: 'Cancelar',
                    preConfirm: () => {
                        const expedicao = document.getElementById('swal-expedicao').value;
                        if (!expedicao) {
                            Swal.showValidationMessage('Data de expedição é obrigatória');
                            return false;
                        }
                        return {
                            expedicao: expedicao,
                            agendamento: document.getElementById('swal-agendamento').value,
                            protocolo: document.getElementById('swal-protocolo').value
                        };
                    }
                }).then((result) => {
                    if (result.isConfirmed) {
                        resolve(result.value);
                    } else {
                        resolve(null);
                    }
                });
            } else {
                // Fallback simples
                const expedicao = prompt('Data de expedição (AAAA-MM-DD):');
                if (expedicao) {
                    resolve({ expedicao, agendamento: null, protocolo: null });
                } else {
                    resolve(null);
                }
            }
        });
    }

    /**
     * 💾 PRESERVAR ESTADO DE EXPANSÃO
     */
    saveExpandedState(pedidoId, isExpanded) {
        if (isExpanded) {
            this.expandedPedidos.add(pedidoId);
        } else {
            this.expandedPedidos.delete(pedidoId);
        }
        localStorage.setItem('expandedPedidos', JSON.stringify([...this.expandedPedidos]));
    }

    restoreExpandedState() {
        const saved = localStorage.getItem('expandedPedidos');
        if (saved) {
            this.expandedPedidos = new Set(JSON.parse(saved));
            // Reabrir pedidos expandidos
            this.expandedPedidos.forEach(pedidoId => {
                const collapse = document.querySelector(`#collapse-${pedidoId}`);
                if (collapse) {
                    collapse.classList.add('show');
                }
            });
        }
    }

    /**
     * 🔒 OBTER CSRF TOKEN
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    /**
     * 🔔 MÉTODOS DE NOTIFICAÇÃO
     */
    async confirmarAcao(titulo, mensagem) {
        if (typeof Swal !== 'undefined') {
            const result = await Swal.fire({
                title: titulo,
                text: mensagem,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#6c757d',
                confirmButtonText: 'Sim, continuar',
                cancelButtonText: 'Cancelar'
            });
            return result.isConfirmed;
        }
        return confirm(`${titulo}\n${mensagem}`);
    }

    mostrarSucesso(mensagem) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'success',
                title: mensagem,
                toast: true,
                position: 'top-end',
                timer: 3000,
                showConfirmButton: false
            });
        } else {
            console.log('✅', mensagem);
        }
    }

    mostrarErro(mensagem) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: mensagem
            });
        } else {
            alert('❌ ' + mensagem);
        }
    }
}

// 🎯 FUNÇÕES GLOBAIS
window.separacaoManager = new SeparacaoManager();

function criarSeparacao(numPedido) {
    window.separacaoManager.criarSeparacaoCompleta(numPedido);
}

function transformarLote(loteId) {
    window.separacaoManager.transformarLoteEmSeparacao(loteId);
}

function excluirSeparacao(separacaoId, numPedido) {
    window.separacaoManager.excluirSeparacao(separacaoId, numPedido);
}

function excluirPreSeparacao(loteId, numPedido) {
    window.separacaoManager.excluirPreSeparacao(loteId, numPedido);
}