/**
 * 🚀 ROTEADOR DE DESTINAÇÃO DE PORTAIS
 * 
 * Este módulo atua como roteador principal, identificando automaticamente
 * qual portal usar baseado no CNPJ do cliente e direcionando para a 
 * implementação específica (Atacadão, Tenda, Sendas, etc.)
 * 
 * @author Sistema de Frete
 * @since 2025-01-09
 */

class PortalAgendamento {
    constructor() {
        this.portaisCarregados = {};
        this.init();
    }

    init() {
        console.log('✅ Roteador de Destinação de Portais inicializado');
        
        // Pré-carregar portal Atacadão
        if (window.PortalAtacadao) {
            this.portaisCarregados.atacadao = window.PortalAtacadao;
            console.log('✅ Portal Atacadão detectado e registrado');
        }
        
        // Pré-carregar portal Sendas (Sistema de Fila)
        if (window.PortalSendas) {
            this.portaisCarregados.sendas = window.PortalSendas;
            console.log('✅ Portal Sendas (Fila) detectado e registrado');
        }
    }

    /**
     * Identifica qual portal usar baseado no lote_id
     */
    async identificarPortal(loteId) {
        try {
            const response = await fetch('/portal/utils/api/identificar-portal-por-lote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ lote_id: loteId })
            });

            const data = await response.json();
            
            if (data.success) {
                console.log(`🎯 Portal identificado para lote ${loteId}: ${data.portal}`);
                return data.portal || 'atacadao'; // Default para atacadao
            }
            
            console.warn(`⚠️ Não foi possível identificar portal para lote ${loteId}, usando atacadao como padrão`);
            return 'atacadao';
            
        } catch (error) {
            console.error('Erro ao identificar portal:', error);
            return 'atacadao'; // Fallback para atacadao
        }
    }

    /**
     * Obtém a instância do portal específico
     */
    async obterPortalEspecifico(loteId) {
        const tipoPortal = await this.identificarPortal(loteId);
        
        // Verificar se o portal está carregado
        if (this.portaisCarregados[tipoPortal]) {
            return this.portaisCarregados[tipoPortal];
        }
        
        // Se não estiver carregado, tentar carregar dinamicamente
        switch(tipoPortal) {
            case 'atacadao':
                if (window.PortalAtacadao) {
                    this.portaisCarregados.atacadao = window.PortalAtacadao;
                    return window.PortalAtacadao;
                }
                break;
            case 'tenda':
                // Futura implementação
                console.warn('Portal Tenda ainda não implementado, usando Atacadão');
                return this.portaisCarregados.atacadao;
            case 'sendas':
                // Futura implementação
                console.warn('Portal Sendas ainda não implementado, usando Atacadão');
                return this.portaisCarregados.atacadao;
        }
        
        // Fallback para Atacadão
        console.warn(`Portal ${tipoPortal} não disponível, usando Atacadão`);
        return this.portaisCarregados.atacadao || window.PortalAtacadao;
    }

    /**
     * 📅 FUNÇÃO PRINCIPAL DE AGENDAMENTO (ROTEADOR)
     * Identifica o portal e delega para a implementação específica
     */
    async agendarNoPortal(loteId, dataAgendamento) {
        console.log(`🚀 Roteando agendamento para lote ${loteId}`);
        
        try {
            const portal = await this.obterPortalEspecifico(loteId);
            
            if (portal && portal.agendarNoPortal) {
                return await portal.agendarNoPortal(loteId, dataAgendamento);
            } else {
                throw new Error('Portal específico não encontrado ou não possui função agendarNoPortal');
            }
        } catch (error) {
            console.error('Erro no roteamento de agendamento:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao processar agendamento. Verifique se o portal está disponível.',
                confirmButtonText: 'OK'
            });
            return false;
        }
    }

    /**
     * 🔍 VERIFICAR STATUS DO AGENDAMENTO (ROTEADOR)
     * Identifica o portal e delega para a implementação específica
     */
    async verificarPortal(loteId) {
        console.log(`🔍 Roteando verificação para lote ${loteId}`);
        
        try {
            const portal = await this.obterPortalEspecifico(loteId);
            
            if (portal && portal.verificarPortal) {
                return await portal.verificarPortal(loteId);
            } else {
                throw new Error('Portal específico não encontrado ou não possui função verificarPortal');
            }
        } catch (error) {
            console.error('Erro no roteamento de verificação:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao verificar status. Verifique se o portal está disponível.',
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * 🔍 VERIFICAR PROTOCOLO NO PORTAL (ROTEADOR)
     * Identifica o portal e delega para a implementação específica
     */
    async verificarProtocoloNoPortal(loteId, protocolo) {
        console.log(`🔍 Roteando verificação de protocolo ${protocolo} para lote ${loteId}`);
        
        try {
            const portal = await this.obterPortalEspecifico(loteId);
            
            if (portal && portal.verificarProtocoloNoPortal) {
                return await portal.verificarProtocoloNoPortal(loteId, protocolo);
            } else {
                throw new Error('Portal específico não encontrado ou não possui função verificarProtocoloNoPortal');
            }
        } catch (error) {
            console.error('Erro no roteamento de verificação de protocolo:', error);
            Swal.fire({
                icon: 'error',
                title: 'Erro',
                text: 'Erro ao verificar protocolo. Verifique se o portal está disponível.',
                confirmButtonText: 'OK'
            });
        }
    }

    /**
     * 📝 ABRIR MODAL DE CADASTRO DE-PARA (ROTEADOR)
     * Por enquanto, usa sempre o Atacadão (pode ser expandido no futuro)
     */
    abrirModalDePara(produtosSemDePara) {
        // Por enquanto, sempre usa Atacadão
        if (window.PortalAtacadao && window.PortalAtacadao.abrirModalDePara) {
            return window.PortalAtacadao.abrirModalDePara(produtosSemDePara);
        }
    }

    /**
     * Obtém token CSRF
     */
    getCSRFToken() {
        return document.querySelector('[name=csrf_token]')?.value || '';
    }

    /**
     * Formatar data para exibição
     */
    formatarData(data) {
        if (!data) return 'N/A';
        
        // Se já for uma string formatada, retornar
        if (typeof data === 'string' && data.includes('/')) {
            return data;
        }
        
        // Converter para objeto Date se necessário
        const dateObj = new Date(data);
        
        // Formatar como DD/MM/YYYY
        const dia = String(dateObj.getDate()).padStart(2, '0');
        const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
        const ano = dateObj.getFullYear();
        
        return `${dia}/${mes}/${ano}`;
    }

    /**
     * Gravar protocolo na separação
     */
    async gravarProtocolo(loteId, protocolo) {
        // Por enquanto, sempre usa Atacadão
        if (window.PortalAtacadao && window.PortalAtacadao.gravarProtocolo) {
            return await window.PortalAtacadao.gravarProtocolo(loteId, protocolo);
        }
    }

    /**
     * Atualizar status da separação
     */
    async atualizarStatusSeparacao(loteId, dataAprovada, confirmado) {
        // Por enquanto, sempre usa Atacadão
        if (window.PortalAtacadao && window.PortalAtacadao.atualizarStatusSeparacao) {
            return await window.PortalAtacadao.atualizarStatusSeparacao(loteId, dataAprovada, confirmado);
        }
    }

    /**
     * Disparar evento de atualização
     */
    dispararEventoAtualizacao(tipo, dados) {
        const evento = new CustomEvent(tipo, { detail: dados });
        window.dispatchEvent(evento);
    }

    /**
     * 🔄 ALIASES PARA COMPATIBILIDADE
     */
    verificarAgendamento(loteId, protocolo) {
        if (protocolo) {
            return this.verificarProtocoloNoPortal(loteId, protocolo);
        } else {
            return this.verificarPortal(loteId);
        }
    }
}

// Inicializar e exportar globalmente
window.PortalAgendamento = new PortalAgendamento();

// Manter compatibilidade com código legado
window.agendarNoPortal = (loteId, dataAgendamento) => {
    return window.PortalAgendamento.agendarNoPortal(loteId, dataAgendamento);
};

window.verificarPortal = (loteId) => {
    return window.PortalAgendamento.verificarPortal(loteId);
};

window.verificarProtocoloNoPortal = (loteId, protocolo) => {
    return window.PortalAgendamento.verificarProtocoloNoPortal(loteId, protocolo);
};

console.log('✅ Roteador de Portais carregado com sucesso');