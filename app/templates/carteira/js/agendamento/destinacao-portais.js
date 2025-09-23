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

        // Registrar portais disponíveis com verificação mais robusta
        this.registrarPortais();

        // Verificar periodicamente por portais carregados tardiamente
        this.verificacaoInicial = setInterval(() => {
            this.registrarPortais();

            // Parar verificação após ter todos os portais essenciais
            if (this.portaisCarregados.atacadao && this.portaisCarregados.sendas) {
                clearInterval(this.verificacaoInicial);
                console.log('✅ Todos os portais essenciais detectados e registrados');
            }
        }, 500);

        // Timeout de segurança - parar verificação após 10 segundos
        setTimeout(() => {
            if (this.verificacaoInicial) {
                clearInterval(this.verificacaoInicial);
                console.log('⏱️ Timeout de verificação de portais atingido');
            }
        }, 10000);
    }

    registrarPortais() {
        // Registrar portal Atacadão se disponível
        if (!this.portaisCarregados.atacadao && window.PortalAtacadao) {
            this.portaisCarregados.atacadao = window.PortalAtacadao;
            console.log('✅ Portal Atacadão detectado e registrado');
        }

        // Registrar portal Sendas se disponível
        if (!this.portaisCarregados.sendas && window.PortalSendas) {
            this.portaisCarregados.sendas = window.PortalSendas;
            console.log('✅ Portal Sendas (Sistema de Comparação) detectado e registrado');
        }
    }

    /**
     * Identifica qual portal usar baseado no lote_id
     */
    async identificarPortal(loteId) {
        console.log(`🔍 [DEBUG] Iniciando identificação de portal para lote: ${loteId}`);

        try {
            const response = await fetch('/portal/utils/api/identificar-portal-por-lote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ lote_id: loteId })
            });

            console.log(`📡 [DEBUG] Response status: ${response.status}`);
            const data = await response.json();
            console.log(`📊 [DEBUG] Response data:`, data);

            if (data.success) {
                console.log(`🎯 Portal identificado para lote ${loteId}: ${data.portal}`);
                const portal = data.portal || 'atacadao';
                console.log(`✅ [DEBUG] Retornando portal: ${portal}`);
                return portal;
            }

            console.warn(`⚠️ Não foi possível identificar portal para lote ${loteId}, usando atacadao como padrão`);
            console.log(`⚠️ [DEBUG] data.success = false, retornando 'atacadao'`);
            return 'atacadao';

        } catch (error) {
            console.error('Erro ao identificar portal:', error);
            console.log(`❌ [DEBUG] Erro capturado, retornando 'atacadao' como fallback`);
            return 'atacadao'; // Fallback para atacadao
        }
    }

    /**
     * Obtém a instância do portal específico
     */
    async obterPortalEspecifico(loteId) {
        console.log(`🔧 [DEBUG] obterPortalEspecifico chamado para lote: ${loteId}`);

        const tipoPortal = await this.identificarPortal(loteId);

        console.log(`🎯 Portal identificado: ${tipoPortal} para lote ${loteId}`);
        console.log(`📦 [DEBUG] Portais carregados no cache:`, Object.keys(this.portaisCarregados));
        console.log(`🔍 [DEBUG] window.PortalSendas existe?`, !!window.PortalSendas);
        console.log(`🔍 [DEBUG] window.PortalAtacadao existe?`, !!window.PortalAtacadao);

        // Tentar buscar portal do cache primeiro
        if (this.portaisCarregados[tipoPortal]) {
            console.log(`✅ Usando Portal ${tipoPortal} do cache`);
            return this.portaisCarregados[tipoPortal];
        }

        console.log(`⏳ [DEBUG] Portal ${tipoPortal} não está no cache, aguardando...`);

        // Aguardar um pouco caso o portal ainda esteja carregando
        await this.aguardarPortal(tipoPortal, 3000); // Aguardar até 3 segundos

        // Se não estiver carregado, tentar carregar dinamicamente
        switch (tipoPortal) {
            case 'atacadao':
                if (window.PortalAtacadao) {
                    console.log('✅ Usando Portal Atacadão');
                    this.portaisCarregados.atacadao = window.PortalAtacadao;
                    return window.PortalAtacadao;
                }
                break;

            case 'sendas':
                // IMPORTANTE: Para Sendas, SEMPRE usar o PortalSendas (Etapa 2 com comparação)
                if (window.PortalSendas) {
                    console.log('✅ Usando Portal Sendas (Sistema de Comparação - Etapa 2)');
                    this.portaisCarregados.sendas = window.PortalSendas;
                    return window.PortalSendas;
                } else {
                    console.error('❌ Portal Sendas não está carregado! Verificar inclusão do script portal-sendas.js');
                    // NÃO fazer fallback para Atacadão quando for Sendas
                    throw new Error('Portal Sendas não está disponível. Verifique se o módulo foi carregado corretamente.');
                }
                break;

            case 'tenda':
                // Futura implementação
                console.warn('Portal Tenda ainda não implementado, usando Atacadão');
                return this.portaisCarregados.atacadao || window.PortalAtacadao;
        }

        // Fallback para Atacadão apenas se não for identificado
        console.warn(`Portal ${tipoPortal} não identificado, usando Atacadão como padrão`);
        return this.portaisCarregados.atacadao || window.PortalAtacadao;
    }

    /**
     * Aguarda o portal ser carregado
     */
    async aguardarPortal(tipoPortal, timeout = 3000) {
        const startTime = Date.now();
        const checkInterval = 100; // Verificar a cada 100ms

        return new Promise((resolve) => {
            const verificar = () => {
                // Verificar se o portal foi carregado
                let portalCarregado = false;

                switch (tipoPortal) {
                    case 'sendas':
                        if (window.PortalSendas) {
                            this.portaisCarregados.sendas = window.PortalSendas;
                            portalCarregado = true;
                            console.log('✅ Portal Sendas detectado após aguardar');
                        }
                        break;
                    case 'atacadao':
                        if (window.PortalAtacadao) {
                            this.portaisCarregados.atacadao = window.PortalAtacadao;
                            portalCarregado = true;
                            console.log('✅ Portal Atacadão detectado após aguardar');
                        }
                        break;
                }

                // Se carregou ou timeout atingido, resolver
                if (portalCarregado || (Date.now() - startTime) >= timeout) {
                    resolve();
                } else {
                    // Continuar verificando
                    setTimeout(verificar, checkInterval);
                }
            };

            verificar();
        });
    }

    /**
     * 📅 FUNÇÃO PRINCIPAL DE AGENDAMENTO (ROTEADOR)
     * Identifica o portal e delega para a implementação específica
     */
    async agendarNoPortal(loteId, dataAgendamento) {
        console.log(`🚀 Roteando agendamento para lote ${loteId}`);

        try {
            // Obter portal específico baseado no CNPJ do lote
            const portal = await this.obterPortalEspecifico(loteId);

            // Log detalhado para debug
            console.log('📊 Portal obtido:', {
                nome: portal?.constructor?.name || 'Desconhecido',
                temFuncaoAgendar: !!(portal && portal.agendarNoPortal),
                portalSendas: portal === window.PortalSendas,
                portalAtacadao: portal === window.PortalAtacadao
            });

            if (portal && portal.agendarNoPortal) {
                // Chamar a função específica do portal identificado
                console.log(`✅ Delegando agendamento para ${portal === window.PortalSendas ? 'SENDAS (Etapa 2)' : 'ATACADÃO'}`);
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
        return window.Security.getCSRFToken();
    }

    /**
     * Formatar data para exibição
     */
    formatarData(data) {
        return window.Formatters.data(data) || 'N/A';
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

console.log('✅ Roteador de Portais carregado com sucesso');