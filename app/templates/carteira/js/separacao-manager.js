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
            
            this.alterarStatus(loteId, 'ABERTO');
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
            
            this.excluirSeparacao(loteId, numPedido);
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
        
        // DESABILITAR TODOS os botões deste pedido para evitar múltiplos cliques
        const todosBotoes = document.querySelectorAll(`[data-pedido="${numPedido}"] .btn-gerar-separacao, [onclick*="criarSeparacao('${numPedido}')"]`);
        
        try {
            // Loading em TODOS os botões
            todosBotoes.forEach(btn => {
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processando...';
            })
            
            const response = await fetch(`/carteira/api/pedido/${numPedido}/gerar-separacao-completa`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',  // 🆕 MUDANÇA: Solicitar JSON para receber lote_id
                    'X-CSRFToken': this.getCSRFToken()  // Adicionar CSRF token
                },
                body: JSON.stringify({
                    expedicao: dataExpedicao.expedicao,
                    agendamento: dataExpedicao.agendamento,
                    protocolo: dataExpedicao.protocolo,
                    agendamento_confirmado: dataExpedicao.agendamento_confirmado || false
                })
            });
            
            // Verificar se a resposta é OK antes de tentar parsear JSON
            if (!response.ok) {
                // Tentar extrair mensagem de erro
                let errorMessage = `Erro HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    // Se não for JSON, tentar texto
                    try {
                        const errorText = await response.text();
                        if (errorText && errorText.length < 200) {
                            errorMessage = errorText;
                        }
                    } catch (e2) {
                        // Manter mensagem padrão
                    }
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                // Como não temos mais targets HTML, atualizar a UI manualmente
                if (data.targets) {
                    // Se ainda retornar targets (modo antigo), aplicar
                    await this.applyTargets(data);
                } else {
                    // 🆕 Modo JSON: Recarregar separações compactas e atualizar contadores
                    if (window.carteiraAgrupada) {
                        // Limpar cache para forçar recarga
                        if (window.separacoesCompactasCache) {
                            delete window.separacoesCompactasCache[numPedido];
                        }
                        
                        // Recarregar separações compactas usando o método correto
                        await window.carteiraAgrupada.carregarSeparacoesEmLoteUnico([numPedido]);
                        
                        // Atualizar contador de separações no botão
                        const btnSeparacoes = document.querySelector(`[data-pedido="${numPedido}"].btn-separacoes`);
                        if (btnSeparacoes) {
                            const contador = btnSeparacoes.querySelector('.contador-separacoes');
                            if (contador) {
                                const qtdAtual = parseInt(contador.textContent) || 0;
                                contador.textContent = qtdAtual + 1;
                            }
                        }
                    }
                }
                
                // Atualizar contadores globais
                if (data.contadores) {
                    this.atualizarContadores(data.contadores);
                }
                
                // Feedback de sucesso
                this.mostrarSucesso(data.message || 'Separação criada com sucesso!');
                
                // Restaurar TODOS os botões após sucesso
                todosBotoes.forEach(btn => {
                    btn.disabled = false;
                    // Manter o texto original do botão (pode ser "Separação" ou "Gerar Separação")
                    btn.innerHTML = '<i class="fas fa-plus me-1"></i> Separação';
                })
                
                // 🆕 AGENDAMENTO AUTOMÁTICO: Verificar se há data de agendamento e pedir confirmação
                if (dataExpedicao.agendamento && !dataExpedicao.protocolo && data.lote_id) {
                    // Aguardar um pouco para garantir que as atualizações foram aplicadas
                    setTimeout(async () => {
                        const confirmarAgendamento = await this.confirmarAgendamentoAutomatico();
                        
                        if (confirmarAgendamento) {
                            console.log('✅ Usuário confirmou agendamento automático');
                            // Chamar função de agendamento do carteiraAgrupada se disponível
                            if (window.carteiraAgrupada && window.carteiraAgrupada.agendarPortal) {
                                window.carteiraAgrupada.agendarPortal(data.lote_id, dataExpedicao.agendamento);
                            } else {
                                // Fallback: redirecionar para portal de agendamento
                                console.log('📆 Redirecionando para portal de agendamento...');
                                this.redirecionarParaPortalAgendamento(data.lote_id, dataExpedicao.agendamento);
                            }
                        } else {
                            console.log('❌ Usuário recusou agendamento automático');
                        }
                    }, 1500);
                }
            } else {
                this.mostrarErro(data.error || 'Erro ao criar separação');
                
                // Restaurar TODOS os botões em caso de erro
                todosBotoes.forEach(btn => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-plus me-1"></i> Separação';
                })
            }
        } catch (error) {
            console.error('Erro ao criar separação:', error);
            // Mostrar mensagem de erro específica se disponível
            const mensagemErro = error.message || 'Erro de comunicação com o servidor';
            this.mostrarErro(mensagemErro);
            
            // Restaurar TODOS os botões
            todosBotoes.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-plus me-1"></i> Separação';
            })
        } finally {
            // Remover da lista de processamento
            this.processingRequests.delete(numPedido);
        }
    }

    /**
     * 🔄 ALTERAR STATUS DA SEPARAÇÃO (MÉTODO UNIFICADO)
     */
    async alterarStatus(loteId, novoStatus) {
        console.log(`🔄 Alterando status do lote ${loteId} para ${novoStatus}`);
        
        const botao = document.querySelector(`[data-lote-id="${loteId}"] .btn-transformar, [data-lote-id="${loteId}"] .btn-reverter`);
        
        try {
            // Loading local no botão
            if (botao) {
                botao.disabled = true;
                const textoLoading = novoStatus === 'ABERTO' ? 'Confirmando...' : 'Revertendo...';
                botao.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${textoLoading}`;
            }
            
            const response = await fetch(`/carteira/api/separacao/${loteId}/alterar-status`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/html',  // Solicitar parciais HTML
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    status: novoStatus
                })
            });
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                // Aplicar parciais HTML
                await this.applyTargets(data);
                
                // Atualizar contadores
                if (data.contadores) {
                    this.atualizarContadores(data.contadores);
                }
                
                const mensagem = novoStatus === 'ABERTO' ? 
                    'Separação confirmada com sucesso!' : 
                    'Separação voltou para previsão!';
                this.mostrarSucesso(data.message || mensagem);
                
                return { success: true, message: mensagem };
            } else {
                this.mostrarErro(data.error || 'Erro ao alterar status');
                
                // Restaurar botão
                if (botao) {
                    botao.disabled = false;
                    const textoOriginal = novoStatus === 'ABERTO' ? 
                        '<i class="fas fa-check me-1"></i>Confirmar' : 
                        '<i class="fas fa-undo me-1"></i>Previsão';
                    botao.innerHTML = textoOriginal;
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
    // Método unificado para excluir separações (qualquer status)
    async excluirSeparacao(loteId, numPedido) {
        if (!await this.confirmarAcao('Excluir Separação', 'Esta ação não pode ser desfeita.')) {
            return { success: false };
        }
        
        console.log(`🗑️ Excluindo separação ${loteId} do pedido ${numPedido}`);
        
        const card = document.querySelector(`[data-lote-id="${loteId}"]`);
        
        try {
            if (card) {
                card.classList.add('deleting');
            }
            
            // UNIFICADO: usar sempre a rota genérica
            const response = await fetch(`/carteira/api/separacao/${loteId}/excluir`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/html',  // Solicitar parciais HTML
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.ok || data.success) {
                this.mostrarSucesso('Separação excluída com sucesso');
                
                // Se temos parciais HTML, aplicar
                if (data.targets) {
                    await this.applyTargets(data);
                }
                
                // Remover card ou recarregar página
                if (card) {
                    card.remove();
                }
                
                // Recarregar se necessário
                if (this.needsReload) {
                    setTimeout(() => location.reload(), 1000);
                }
                
                return { success: true };
            } else {
                throw new Error(data.error || 'Erro ao excluir');
            }
        } catch (error) {
            if (card) {
                card.classList.remove('deleting');
            }
            this.mostrarErro(`Erro ao excluir: ${error.message}`);
            return { success: false, error: error.message };
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
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="swal-agendamento-confirmado">
                                <label class="form-check-label" for="swal-agendamento-confirmado">
                                    <i class="fas fa-check-circle text-success"></i> Agenda Confirmada
                                </label>
                            </div>
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
                            protocolo: document.getElementById('swal-protocolo').value,
                            agendamento_confirmado: document.getElementById('swal-agendamento-confirmado').checked
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

    /**
     * 🆕 CONFIRMAR AGENDAMENTO AUTOMÁTICO
     * Solicita confirmação do usuário para agendar automaticamente no portal
     */
    async confirmarAgendamentoAutomatico() {
        if (typeof Swal !== 'undefined') {
            const result = await Swal.fire({
                title: 'Agendamento Automático',
                text: 'Deseja realizar o agendamento no portal automaticamente?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Sim, agendar',
                cancelButtonText: 'Não',
                confirmButtonColor: '#28a745',
                cancelButtonColor: '#6c757d'
            });
            return result.isConfirmed;
        } else {
            return confirm('Deseja realizar o agendamento no portal automaticamente?\n\n"OK" = Sim, agendar no portal\n"Cancelar" = Não agendar');
        }
    }

    /**
     * 🆕 REDIRECIONAR PARA PORTAL DE AGENDAMENTO
     * Função de fallback caso carteiraAgrupada não esteja disponível
     */
    redirecionarParaPortalAgendamento(loteId, dataAgendamento) {
        console.log(`📆 Preparando redirecionamento para portal de agendamento`);
        console.log(`   Lote: ${loteId}`);
        console.log(`   Data: ${dataAgendamento}`);
        
        // Tentar chamar a função do workspace se disponível
        if (window.workspace && window.workspace.agendarNoPortal) {
            window.workspace.agendarNoPortal(loteId, dataAgendamento);
        } else {
            // Se não houver função disponível, apenas logar
            console.warn('⚠️ Função de agendamento não disponível. Implemente manualmente o redirecionamento para o portal.');
            this.mostrarSucesso(`Separação criada! Agora você pode agendar o lote ${loteId} para ${this.formatarDataBR(dataAgendamento)} no portal.`);
        }
    }

    /**
     * 🆕 FORMATAR DATA PARA EXIBIÇÃO BR
     */
    formatarDataBR(data) {
        if (!data) return '';
        const [ano, mes, dia] = data.split('-');
        return `${dia}/${mes}/${ano}`;
    }

    /**
     * 🎯 REGRAS DE PERMISSÃO POR STATUS
     * Centraliza todas as regras de negócio sobre o que é permitido em cada status
     */
    podeEditarDatas(status) {
        return ['PREVISAO', 'ABERTO'].includes(status);
    }
    
    podeAdicionarProdutos(status) {
        return ['PREVISAO', 'ABERTO'].includes(status);
    }
    
    podeRemoverProdutos(status) {
        return ['PREVISAO', 'ABERTO'].includes(status);
    }
    
    podeCancelar(status) {
        return ['PREVISAO', 'ABERTO'].includes(status);
    }
    
    podeConfirmar(status) {
        // Só pode confirmar se estiver em PREVISAO (transformar em ABERTO)
        return status === 'PREVISAO';
    }
    
    podeCotar(status) {
        // Só pode cotar se estiver ABERTO
        return status === 'ABERTO';
    }
    
    podeVerCotacao(status) {
        // Pode ver cotação se estiver COTADO ou status posteriores
        return ['COTADO', 'EMBARCADO', 'FATURADO'].includes(status);
    }
    
    podeEmbarcar(status) {
        // Só pode embarcar se estiver COTADO
        return status === 'COTADO';
    }
    
    /**
     * 🎨 OBTER COR DO STATUS
     * Retorna a classe Bootstrap apropriada para cada status
     */
    obterCorStatus(status) {
        const cores = {
            'PREVISAO': 'secondary',    // Cinza claro
            'ABERTO': 'warning',        // Amarelo
            'COTADO': 'primary',        // Azul
            'EMBARCADO': 'success',     // Verde
            'FATURADO': 'success',      // Verde
            'NF_CD': 'danger'           // Vermelho
        };
        return cores[status] || 'secondary';
    }
    
    /**
     * 🏷️ OBTER LABEL DO STATUS
     * Retorna o texto amigável para cada status
     */
    obterLabelStatus(status) {
        const labels = {
            'PREVISAO': 'Previsão',
            'ABERTO': 'Aberto',
            'COTADO': 'Cotado',
            'EMBARCADO': 'Embarcado',
            'FATURADO': 'Faturado',
            'NF_CD': 'NF no CD'
        };
        return labels[status] || status;
    }

    /**
     * 🔄 CRIAR SEPARAÇÃO COM STATUS PREVISAO
     * Para drag & drop e criação manual (substitui pré-separação)
     */
    async criarSeparacaoPrevisao(numPedido, produtos, dataExpedicao) {
        try {
            const response = await fetch('/carteira/api/separacao/salvar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    produtos: produtos,
                    expedicao: dataExpedicao,
                    status: 'PREVISAO'  // Sempre criar como PREVISAO (substitui pré-separação)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✅ Separação PREVISAO criada com sucesso');
                return result;
            } else {
                throw new Error(result.error || 'Erro ao criar separação');
            }
        } catch (error) {
            console.error('❌ Erro ao criar separação PREVISAO:', error);
            throw error;
        }
    }

    /**
     * 🔍 CARREGAR SEPARAÇÕES POR STATUS
     * Busca apenas separações com status específico
     */
    async carregarSeparacoesPorStatus(numPedido, status) {
        try {
            const response = await fetch(`/carteira/api/pedido/${numPedido}/separacoes?status=${status}`);
            const result = await response.json();
            
            if (result.success) {
                return result.separacoes;
            } else {
                console.warn(`Nenhuma separação ${status} encontrada para pedido ${numPedido}`);
                return [];
            }
        } catch (error) {
            console.error(`Erro ao carregar separações ${status}:`, error);
            return [];
        }
    }

    /**
     * ↩️ VOLTAR SEPARAÇÃO PARA PREVISÃO
     * Transforma uma separação ABERTO de volta para PREVISAO
     */
    async voltarParaPrevisao(loteId) {
        try {
            const confirmar = await this.confirmarAcao(
                'Voltar para Previsão?',
                'Esta separação voltará ao status de previsão. Deseja continuar?',
                'warning'
            );
            
            if (!confirmar) return { success: false };

            const response = await fetch(`/carteira/api/separacao/${loteId}/alterar-status`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    status: 'PREVISAO'  // CORRIGIDO: usar 'status' ao invés de 'novo_status'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.mostrarSucesso('Separação voltou para previsão');
                // Recarregar a página ou atualizar o card
                if (window.workspace) {
                    window.workspace.recarregarLotes();
                }
                return result;
            } else {
                throw new Error(result.error || 'Erro ao voltar para previsão');
            }
        } catch (error) {
            console.error('❌ Erro ao voltar para previsão:', error);
            this.mostrarErro(error.message);
            throw error;
        }
    }

    /**
     * 🔄 CONFIRMAR AÇÃO COM MODAL
     */
    async confirmarAcao(titulo, texto, icone = 'question') {
        if (typeof Swal !== 'undefined') {
            const result = await Swal.fire({
                title: titulo,
                text: texto,
                icon: icone,
                showCancelButton: true,
                confirmButtonColor: '#3085d6',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Sim, continuar',
                cancelButtonText: 'Cancelar'
            });
            return result.isConfirmed;
        } else {
            return confirm(`${titulo}\n\n${texto}`);
        }
    }
}

// 🎯 FUNÇÕES GLOBAIS
window.separacaoManager = new SeparacaoManager();

function criarSeparacao(numPedido) {
    window.separacaoManager.criarSeparacaoCompleta(numPedido);
}

function transformarLote(loteId) {
    window.separacaoManager.alterarStatus(loteId, 'ABERTO');
}

// Funções globais unificadas
function excluirSeparacao(loteId, numPedido) {
    window.separacaoManager.excluirSeparacao(loteId, numPedido);
}


function voltarParaPrevisao(loteId) {
    window.separacaoManager.voltarParaPrevisao(loteId);
}