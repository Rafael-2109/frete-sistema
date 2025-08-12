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
     * 🎯 AUTO-CRIAR PRÉ-SEPARAÇÃO NO DRAG & DROP
     * CASO 3: Criar uma pré-separação ao realizar o "drag & drop" para o lote de maneira automática
     * Um produto "dropado" em um lote vazio deve se tornar uma nova pré-separação automaticamente
     */
    async criarPreSeparacaoAutomatica(numPedido, codProduto, quantidade, dataExpedicao, loteId = null) {
        console.log(`🎯 CASO 3: Auto-criar pré-separação - ${numPedido} - ${codProduto}`);
        
        try {
            // Se não foi fornecido lote_id, gerar baseado na data
            if (!loteId) {
                loteId = this.gerarLoteIdPreSeparacao(dataExpedicao);
            }

            // Validar dados
            this.validarDadosPreSeparacao(numPedido, codProduto, loteId, quantidade);

            const response = await fetch('/carteira/api/pre-separacao/salvar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    num_pedido: numPedido,
                    cod_produto: codProduto,
                    lote_id: loteId,
                    qtd_selecionada_usuario: quantidade,
                    data_expedicao_editada: dataExpedicao
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log(`✅ Pré-separação criada automaticamente: ${result.message}`);
                
                // Atualizar dados locais se workspace estiver disponível
                if (this.workspace) {
                    this.atualizarDadosLocais(loteId, result.dados);
                }
                
                return {
                    success: true,
                    lote_id: result.lote_id,
                    pre_separacao_id: result.pre_separacao_id,
                    dados: result.dados
                };
            } else {
                console.error(`❌ Erro ao criar pré-separação: ${result.error}`);
                return {
                    success: false,
                    error: result.error
                };
            }
            
        } catch (error) {
            console.error('Erro ao criar pré-separação automática:', error);
            return {
                success: false,
                error: error.message || 'Erro interno'
            };
        }
    }

    /**
     * Salvar pré-separação via API (drag & drop - método legado)
     */
    async salvarPreSeparacao(numPedido, codProduto, loteId, quantidade, dataExpedicao = null) {
        // Usar a nova função automática como padrão
        const dataExpedicaoFinal = dataExpedicao || this.obterDataExpedicaoDefault();
        return await this.criarPreSeparacaoAutomatica(numPedido, codProduto, quantidade, dataExpedicaoFinal, loteId);
    }

    /**
     * Remover pré-separação via API
     */
    async removerPreSeparacao(preSeparacaoId) {
        try {
            const response = await fetch(`/carteira/api/pre-separacao/${preSeparacaoId}/remover`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
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
     * 🎯 DELEGAR PARA SEPARACAO-MANAGER (Caso 2)
     */
    async confirmarSeparacao(loteId, dadosConfirmacao) {
        console.log(`🔄 Delegando transformação do lote ${loteId} para separacao-manager`);
        
        // 🎯 USAR a nova rota unificada do separacao-manager
        if (window.separacaoManager) {
            await window.separacaoManager.transformarLoteEmSeparacao(loteId);
            return { success: true, message: 'Lote transformado em separação com sucesso' };
        } else {
            console.error('❌ Separação Manager não disponível');
            throw new Error('Sistema de separação não está disponível');
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
    
    /**
     * Obter CSRF Token de forma consistente
     */
    getCSRFToken() {
        // Tentar várias formas de obter o CSRF token
        // 1. Cookie
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        if (cookieValue) return cookieValue;
        
        // 2. Meta tag
        const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (metaToken) return metaToken;
        
        // 3. Input hidden em formulários
        const inputToken = document.querySelector('input[name="csrf_token"]')?.value;
        if (inputToken) return inputToken;
        
        // 4. Window global
        if (window.csrfToken) return window.csrfToken;
        
        console.warn('⚠️ CSRF Token não encontrado');
        return '';
    }
}

// 🎯 FUNÇÕES GLOBAIS PARA PRÉ-SEPARAÇÃO

/**
 * FUNÇÃO GLOBAL PARA DRAG & DROP AUTOMÁTICO - CASO 3
 */
function criarPreSeparacaoAuto(numPedido, codProduto, quantidade, dataExpedicao, loteId = null) {
    if (window.preSeparacaoManagerGlobal) {
        return window.preSeparacaoManagerGlobal.criarPreSeparacaoAutomatica(numPedido, codProduto, quantidade, dataExpedicao, loteId);
    } else {
        console.error('❌ Pré-Separação Manager global não inicializado');
        return { success: false, error: 'Manager não inicializado' };
    }
}

/**
 * FUNÇÃO GLOBAL PARA SALVAR PRÉ-SEPARAÇÃO
 */
function salvarPreSeparacao(numPedido, codProduto, loteId, quantidade, dataExpedicao = null) {
    if (window.preSeparacaoManagerGlobal) {
        return window.preSeparacaoManagerGlobal.salvarPreSeparacao(numPedido, codProduto, loteId, quantidade, dataExpedicao);
    } else {
        console.error('❌ Pré-Separação Manager global não inicializado');
        return { success: false, error: 'Manager não inicializado' };
    }
}

/**
 * FUNÇÃO GLOBAL PARA REMOVER PRÉ-SEPARAÇÃO
 */
function removerPreSeparacao(preSeparacaoId) {
    if (window.preSeparacaoManagerGlobal) {
        return window.preSeparacaoManagerGlobal.removerPreSeparacao(preSeparacaoId);
    } else {
        console.error('❌ Pré-Separação Manager global não inicializado');
        return { success: false, error: 'Manager não inicializado' };
    }
}

/**
 * FUNÇÃO GLOBAL PARA CONFIRMAR SEPARAÇÃO
 */
function confirmarSeparacaoPreSeparacao(loteId, dadosConfirmacao) {
    if (window.preSeparacaoManagerGlobal) {
        return window.preSeparacaoManagerGlobal.confirmarSeparacao(loteId, dadosConfirmacao);
    } else {
        console.error('❌ Pré-Separação Manager global não inicializado');
        return { success: false, error: 'Manager não inicializado' };
    }
}

// Disponibilizar globalmente
window.PreSeparacaoManager = PreSeparacaoManager;

// Inicializar instância global para funções standalone (sem workspace)
document.addEventListener('DOMContentLoaded', function() {
    if (!window.preSeparacaoManagerGlobal) {
        window.preSeparacaoManagerGlobal = new PreSeparacaoManager(null);
        console.log('✅ Pré-Separação Manager Global inicializado');
    }
});