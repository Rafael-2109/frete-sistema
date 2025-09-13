/**
 * 🎯 MÓDULO DE AGENDAMENTO NO PORTAL SENDAS
 * 
 * Sistema de fila inteligente:
 * - Adiciona solicitações individuais na fila
 * - Processa em lote automaticamente
 * - Notifica quando concluído
 */

class PortalSendas {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Módulo Portal Sendas inicializado');
        this.verificarFilaPeriodicamente();
    }

    /**
     * 📅 FUNÇÃO PRINCIPAL - Adiciona na fila
     * Em vez de agendar imediatamente, adiciona na fila para processar em lote
     */
    async agendarNoPortal(loteId, dataAgendamento) {
        console.log(`📅 [Sendas] Adicionando lote ${loteId} na fila`);
        
        try {
            // Determinar data de expedição (D-1 do agendamento se não fornecida)
            let dataExpedicao = null;
            if (dataAgendamento) {
                const agendDate = new Date(dataAgendamento);
                const expedDate = new Date(agendDate);
                expedDate.setDate(expedDate.getDate() - 1);
                dataExpedicao = expedDate.toISOString().split('T')[0];
            }
            
            // Adicionar na fila
            const response = await fetch('/portal/sendas/fila/adicionar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    tipo_origem: 'separacao',
                    documento_origem: loteId,
                    data_expedicao: dataExpedicao,
                    data_agendamento: dataAgendamento
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Mostrar status da fila
                await this.mostrarStatusFila(result);
                
                // Perguntar se quer processar agora
                const processar = await Swal.fire({
                    icon: 'question',
                    title: 'Item Adicionado à Fila',
                    html: `
                        <div class="text-center">
                            <p><strong>${result.itens_adicionados}</strong> itens adicionados à fila do Sendas</p>
                            <div class="mt-3">
                                <p class="text-info">
                                    <i class="fas fa-boxes"></i> 
                                    Total na fila: <strong>${result.pendentes_total} itens</strong>
                                </p>
                            </div>
                            <hr>
                            <p>Deseja processar a fila agora?</p>
                            <small class="text-muted">
                                A fila também é processada automaticamente quando atinge 5 itens
                            </small>
                        </div>
                    `,
                    showCancelButton: true,
                    confirmButtonText: 'Processar Agora',
                    cancelButtonText: 'Aguardar Mais',
                    confirmButtonColor: '#28a745',
                    cancelButtonColor: '#6c757d'
                });
                
                if (processar.isConfirmed) {
                    await this.processarFila();
                }
                
                return true;
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Erro',
                    text: result.message || 'Erro ao adicionar na fila',
                    confirmButtonText: 'OK'
                });
                return false;
            }
            
        } catch (error) {
            console.error('Erro ao adicionar na fila:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao adicionar na fila do Sendas',
                confirmButtonText: 'OK'
            });
            return false;
        }
    }
    
    /**
     * 📊 Mostra status da fila
     */
    async mostrarStatusFila(dados) {
        // Criar notificação toast discreta
        const toastHtml = `
            <div class="toast show position-fixed top-0 end-0 m-3" style="z-index: 9999;">
                <div class="toast-header bg-info text-white">
                    <i class="fas fa-boxes me-2"></i>
                    <strong class="me-auto">Fila Sendas</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    <strong>${dados.pendentes_total}</strong> itens aguardando processamento
                    ${dados.pendentes_total >= 5 ? 
                        '<br><span class="text-success">Pronto para processar!</span>' : 
                        '<br><small class="text-muted">Aguardando mais itens...</small>'}
                </div>
            </div>
        `;
        
        // Adicionar ao DOM
        const toastContainer = document.createElement('div');
        toastContainer.innerHTML = toastHtml;
        document.body.appendChild(toastContainer);
        
        // Remover após 5 segundos
        setTimeout(() => {
            toastContainer.remove();
        }, 5000);
    }
    
    /**
     * 🚀 Processa a fila em lote
     */
    async processarFila() {
        console.log('🚀 [Sendas] Processando fila em lote');
        
        Swal.fire({
            title: 'Processando Fila Sendas',
            html: `
                <div class="text-center">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Processando...</span>
                    </div>
                    <p>Preparando lote para envio ao portal...</p>
                </div>
            `,
            allowOutsideClick: false,
            showConfirmButton: false
        });
        
        try {
            // Obter itens da fila agrupados
            const statusResponse = await fetch('/portal/sendas/fila/status?detalhes=true');
            const statusData = await statusResponse.json();
            
            if (!statusData.detalhes || statusData.detalhes.length === 0) {
                Swal.fire({
                    icon: 'info',
                    title: 'Fila Vazia',
                    text: 'Não há itens na fila para processar',
                    confirmButtonText: 'OK'
                });
                return;
            }
            
            // Preparar dados para o endpoint de lote existente
            const cnpjsParaProcessar = statusData.detalhes.map(item => ({
                cnpj: item.cnpj,
                expedicao: new Date(item.data_agendamento).toISOString().split('T')[0],
                agendamento: item.data_agendamento
            }));
            
            // Chamar o endpoint de processamento em lote
            const response = await fetch('/carteira/programacao-lote/api/processar-agendamento-sendas-async', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    portal: 'sendas',
                    cnpjs: cnpjsParaProcessar
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.job_id) {
                // Marcar itens como processados
                await fetch('/portal/sendas/fila/processar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });
                
                Swal.fire({
                    icon: 'success',
                    title: 'Fila Processada!',
                    html: `
                        <div class="text-center">
                            <p><strong>${cnpjsParaProcessar.length}</strong> grupos enviados para processamento</p>
                            <p class="text-muted mt-2">
                                <i class="fas fa-info-circle"></i> 
                                O processamento está sendo feito em background
                            </p>
                        </div>
                    `,
                    confirmButtonText: 'OK'
                });
            } else {
                throw new Error(result.error || 'Erro no processamento');
            }
            
        } catch (error) {
            console.error('Erro ao processar fila:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao processar fila: ' + error.message,
                confirmButtonText: 'OK'
            });
        }
    }
    
    /**
     * 🔍 Verifica status de agendamento
     */
    async verificarPortal(loteId) {
        // Por enquanto, apenas mostrar status da fila
        const response = await fetch('/portal/sendas/fila/status');
        const data = await response.json();
        
        Swal.fire({
            icon: 'info',
            title: 'Status da Fila Sendas',
            html: `
                <div class="text-center">
                    <p><strong>${data.pendentes_total}</strong> itens pendentes</p>
                    ${Object.entries(data.pendentes_por_cnpj).map(([cnpj, total]) => 
                        `<p><small>${cnpj}: ${total} itens</small></p>`
                    ).join('')}
                </div>
            `,
            confirmButtonText: 'OK'
        });
    }
    
    /**
     * 🔄 Verifica fila periodicamente
     */
    verificarFilaPeriodicamente() {
        // A cada 5 minutos, verificar se tem itens suficientes para processar
        setInterval(async () => {
            try {
                const response = await fetch('/portal/sendas/fila/status');
                const data = await response.json();
                
                // Se tem mais de 10 itens, sugerir processamento
                if (data.pendentes_total >= 10) {
                    console.log(`[Sendas] ${data.pendentes_total} itens na fila - sugerindo processamento`);
                    
                    // Mostrar notificação discreta
                    this.mostrarStatusFila(data);
                }
            } catch (error) {
                console.error('Erro ao verificar fila:', error);
            }
        }, 5 * 60 * 1000); // 5 minutos
    }
    
    /**
     * Obtém CSRF Token
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// Exportar globalmente
window.PortalSendas = new PortalSendas();

console.log('✅ Portal Sendas carregado - Sistema de fila ativo');