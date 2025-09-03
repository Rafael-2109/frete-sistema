/**
 * 🌐 WORKSPACE API MODULE
 * Centraliza todas as chamadas de API do workspace
 * Facilita manutenção e adiciona tratamento de erro consistente
 */

class WorkspaceAPI {
    constructor() {
        this.baseUrl = '/carteira/api';
        this.abortControllers = new Map();
    }

    /**
     * 🎯 BUSCAR DADOS DO WORKSPACE
     * Retorna produtos e informações do pedido
     */
    async buscarWorkspace(numPedido) {
        const response = await this.fetchWithAbort(
            `workspace_${numPedido}`,
            `${this.baseUrl}/pedido/${numPedido}/workspace`
        );
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao carregar workspace');
        }
        
        return data;
    }

    /**
     * 🎯 BUSCAR PRÉ-SEPARAÇÕES
     * Retorna lotes de pré-separação existentes
     */
    async buscarPreSeparacoes(numPedido) {
        const response = await this.fetchWithAbort(
            `pre_separacoes_${numPedido}`,
            `${this.baseUrl}/pedido/${numPedido}/pre-separacoes`
        );
        
        const data = await response.json();
        return data;
    }

    /**
     * 🎯 BUSCAR SEPARAÇÕES CONFIRMADAS
     * Retorna separações já confirmadas do pedido
     */
    async buscarSeparacoes(numPedido) {
        const response = await this.fetchWithAbort(
            `separacoes_${numPedido}`,
            `${this.baseUrl}/pedido/${numPedido}/separacoes-completas`
        );
        
        const data = await response.json();
        return data;
    }

    /**
     * 🎯 BUSCAR DADOS DE ESTOQUE (ASSÍNCRONO)
     * Carrega dados detalhados de estoque após renderização inicial
     * Implementa retry logic e timeout maior para evitar falhas
     */
    async buscarEstoqueAssincrono(numPedido, tentativa = 1, maxTentativas = 3) {
        try {
            const response = await this.fetchWithAbort(
                `estoque_${numPedido}`,
                `${this.baseUrl}/pedido/${numPedido}/workspace-estoque`,
                {
                    // Aumentar timeout para 30 segundos
                    timeout: 30000
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao carregar estoque');
            }
            
            return data;
        } catch (error) {
            console.warn(`⚠️ Tentativa ${tentativa} de ${maxTentativas} falhou para estoque do pedido ${numPedido}: ${error.message}`);
            
            // Se não for a última tentativa e não for abort, tentar novamente
            if (tentativa < maxTentativas && error.name !== 'AbortError') {
                // Aguardar progressivamente antes de tentar novamente
                const delay = tentativa * 1000; // 1s, 2s, 3s
                console.log(`⏳ Aguardando ${delay}ms antes da próxima tentativa...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                
                return this.buscarEstoqueAssincrono(numPedido, tentativa + 1, maxTentativas);
            }
            
            // Se todas as tentativas falharam, lançar o erro
            throw error;
        }
    }

    /**
     * 🎯 ATUALIZAR DATAS DE SEPARAÇÃO
     * Atualiza expedição, agendamento e protocolo
     */
    async atualizarDatas(tipo, loteId, dados) {
        const endpoint = tipo === 'pre-separacao'
            ? `${this.baseUrl}/pre-separacao/${loteId}/atualizar-datas`
            : `${this.baseUrl}/separacao/${loteId}/atualizar-datas`;

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(dados)
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao atualizar datas');
        }
        
        return data;
    }

    /**
     * 🎯 ADICIONAR PRODUTO AO LOTE
     * Adiciona ou atualiza produto em um lote de pré-separação
     */
    async adicionarProdutoLote(loteId, produto) {
        const response = await fetch(`${this.baseUrl}/pre-separacao/${loteId}/adicionar-produto`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(produto)
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao adicionar produto');
        }
        
        return data;
    }

    /**
     * 🎯 REMOVER PRODUTO DO LOTE
     * Remove produto de um lote de pré-separação
     */
    async removerProdutoLote(loteId, codProduto) {
        const response = await fetch(`${this.baseUrl}/pre-separacao/${loteId}/remover-produto`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ cod_produto: codProduto })
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao remover produto');
        }
        
        return data;
    }

    /**
     * 🎯 CONFIRMAR PRÉ-SEPARAÇÃO
     * Transforma pré-separação em separação confirmada
     */
    async confirmarPreSeparacao(loteId) {
        const response = await fetch(`${this.baseUrl}/pre-separacao/${loteId}/confirmar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao confirmar pré-separação');
        }
        
        return data;
    }

    /**
     * 🎯 EXCLUIR LOTE
     * Remove lote de pré-separação
     */
    async excluirLote(loteId) {
        const response = await fetch(`${this.baseUrl}/pre-separacao/${loteId}/excluir`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao excluir lote');
        }
        
        return data;
    }

    /**
     * 🛠️ FETCH COM ABORT CONTROLLER E TIMEOUT
     * Permite cancelar requisições em andamento e configurar timeout
     */
    async fetchWithAbort(key, url, options = {}) {
        // REMOVIDO: Não cancelar requisição anterior para permitir múltiplos pedidos expandidos
        // Cada pedido deve carregar independentemente
        
        // Criar novo AbortController único para esta requisição
        const controller = new AbortController();
        const uniqueKey = `${key}_${Date.now()}_${Math.random()}`; // Chave única para cada requisição
        this.abortControllers.set(uniqueKey, controller);
        
        // Configurar timeout (padrão: 10 segundos, pode ser sobrescrito)
        const timeout = options.timeout || 10000;
        const timeoutId = setTimeout(() => {
            console.warn(`⏱️ Timeout após ${timeout}ms para ${url}`);
            controller.abort();
        }, timeout);

        try {
            console.log(`📡 WorkspaceAPI: Fazendo requisição para ${url} (timeout: ${timeout}ms)`);
            
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });

            // Verificar se a resposta é HTML (erro 404 ou similar)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.error(`❌ WorkspaceAPI: Recebeu HTML em vez de JSON de ${url}`);
                throw new Error(`Endpoint não encontrado: ${url} retornou HTML em vez de JSON`);
            }

            // Limpar timeout e controller após sucesso
            clearTimeout(timeoutId);
            this.abortControllers.delete(uniqueKey);
            
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                console.log(`Requisição ${uniqueKey} cancelada ou timeout`);
                // Melhorar mensagem de erro para timeout
                error.message = `Timeout na requisição para ${url}`;
            }
            // Limpar controller em caso de erro também
            this.abortControllers.delete(uniqueKey);
            throw error;
        }
    }

    /**
     * 🛑 CANCELAR TODAS AS REQUISIÇÕES
     * Útil ao trocar de pedido ou limpar workspace
     */
    cancelarTodasRequisicoes() {
        this.abortControllers.forEach(controller => {
            controller.abort();
        });
        this.abortControllers.clear();
    }
}

// Disponibilizar globalmente
window.WorkspaceAPI = WorkspaceAPI;