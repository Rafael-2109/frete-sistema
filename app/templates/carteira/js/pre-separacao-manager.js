/**
 * 📦 GERENCIADOR DE PRÉ-SEPARAÇÕES
 * Responsável pela persistência e gerenciamento de pré-separações via API
 */

class PreSeparacaoManager {
    constructor(workspace) {
        this.workspace = workspace;
        this.init();
    }

    init() {
        console.log('✅ Pré-Separação Manager inicializado');
    }

    /**
     * Salvar pré-separação via API (drag & drop)
     */
    async salvarPreSeparacao(numPedido, codProduto, loteId, quantidade) {
        try {
            const response = await fetch('/carteira/api/pre-separacao/salvar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    cod_produto: codProduto,
                    lote_id: loteId,
                    qtd_selecionada_usuario: quantidade,
                    data_expedicao_editada: this.obterDataExpedicaoDefault()
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Erro ao salvar pré-separação');
            }

            return result;

        } catch (error) {
            console.error('❌ Erro ao salvar pré-separação:', error);
            throw error;
        }
    }

    /**
     * Remover pré-separação via API
     */
    async removerPreSeparacao(preSeparacaoId) {
        try {
            const response = await fetch(`/carteira/api/pre-separacao/${preSeparacaoId}/remover`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Erro ao remover pré-separação');
            }

            return result;

        } catch (error) {
            console.error('❌ Erro ao remover pré-separação:', error);
            throw error;
        }
    }

    /**
     * Carregar pré-separações existentes de um pedido
     */
    async carregarPreSeparacoes(numPedido) {
        try {
            const response = await fetch(`/carteira/api/pedido/${numPedido}/pre-separacoes`);
            const result = await response.json();

            if (!response.ok) {
                // Se não encontrou, não é erro (pedido sem pré-separações)
                return { success: true, lotes: [] };
            }

            return result;

        } catch (error) {
            console.error('❌ Erro ao carregar pré-separações:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Confirmar pré-separação como separação definitiva
     */
    async confirmarSeparacao(loteId, dadosConfirmacao) {
        try {
            const response = await fetch(`/carteira/api/pre-separacao/lote/${loteId}/confirmar-separacao`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agendamento: dadosConfirmacao.agendamento,
                    protocolo: dadosConfirmacao.protocolo
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Erro ao confirmar separação');
            }

            return result;

        } catch (error) {
            console.error('❌ Erro ao confirmar separação:', error);
            throw error;
        }
    }

    /**
     * Processar dados de pré-separações carregadas
     */
    processarPreSeparacoesCarregadas(lotes) {
        const preSeparacoesMap = new Map();

        lotes.forEach(lote => {
            preSeparacoesMap.set(lote.lote_id, {
                produtos: lote.produtos.map(p => ({
                    codProduto: p.cod_produto,
                    quantidade: p.quantidade,
                    valor: p.valor,
                    peso: p.peso,
                    pallet: p.pallet,
                    preSeparacaoId: p.pre_separacao_id,
                    loteId: lote.lote_id,
                    status: 'pre_separacao'
                })),
                totais: lote.totais,
                status: 'pre_separacao',
                dataExpedicao: lote.data_expedicao
            });
        });

        return preSeparacoesMap;
    }

    /**
     * Atualizar dados locais após operação de API
     */
    atualizarDadosLocais(loteId, dadosResposta) {
        const loteData = this.workspace.preSeparacoes.get(loteId) || {
            produtos: [],
            totais: { valor: 0, peso: 0, pallet: 0 }
        };

        // Verificar se produto já existe no lote
        const produtoExistente = loteData.produtos.find(p => p.codProduto === dadosResposta.cod_produto);
        
        if (produtoExistente) {
            // Atualizar dados do produto existente
            produtoExistente.quantidade = dadosResposta.quantidade;
            produtoExistente.preSeparacaoId = dadosResposta.pre_separacao_id || produtoExistente.preSeparacaoId;
            produtoExistente.valor = dadosResposta.valor;
            produtoExistente.peso = dadosResposta.peso;
            produtoExistente.pallet = dadosResposta.pallet;
        } else {
            // Adicionar novo produto com dados da API
            loteData.produtos.push({
                codProduto: dadosResposta.cod_produto,
                quantidade: dadosResposta.quantidade,
                valor: dadosResposta.valor,
                peso: dadosResposta.peso,
                pallet: dadosResposta.pallet,
                preSeparacaoId: dadosResposta.pre_separacao_id,
                loteId: loteId,
                status: 'pre_separacao'
            });
        }

        // Atualizar Map local
        this.workspace.preSeparacoes.set(loteId, loteData);
        return loteData;
    }

    /**
     * Remover produto dos dados locais
     */
    removerDadosLocais(loteId, codProduto) {
        const loteData = this.workspace.preSeparacoes.get(loteId);
        if (!loteData) return null;

        // Encontrar produto para obter dados antes de remover
        const produto = loteData.produtos.find(p => p.codProduto === codProduto);
        if (!produto) return null;

        // Remover do array
        loteData.produtos = loteData.produtos.filter(p => p.codProduto !== codProduto);
        
        return produto;
    }

    /**
     * Atualizar status de lote (pré-separação → separação)
     */
    atualizarStatusLote(loteId, novoStatus) {
        const loteData = this.workspace.preSeparacoes.get(loteId);
        if (loteData) {
            loteData.status = novoStatus;
            loteData.produtos.forEach(p => p.status = novoStatus);
            return loteData;
        }
        return null;
    }

    /**
     * Utilitários
     */
    obterDataExpedicaoDefault() {
        // Data padrão: amanhã
        const amanha = new Date();
        amanha.setDate(amanha.getDate() + 1);
        return amanha.toISOString().split('T')[0];
    }

    validarDadosPreSeparacao(numPedido, codProduto, loteId, quantidade) {
        if (!numPedido || !codProduto || !loteId) {
            throw new Error('Dados obrigatórios ausentes: numPedido, codProduto, loteId');
        }

        if (!quantidade || quantidade <= 0) {
            throw new Error('Quantidade deve ser maior que zero');
        }

        return true;
    }

    gerarLoteIdPreSeparacao(dataExpedicao) {
        return `PRE-${dataExpedicao}`;
    }
}

// Disponibilizar globalmente
window.PreSeparacaoManager = PreSeparacaoManager;