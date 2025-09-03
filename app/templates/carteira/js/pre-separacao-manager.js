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
                dataExpedicao: lote.data_expedicao,
                data_agendamento: lote.data_agendamento,
                agendamento_confirmado: lote.agendamento_confirmado || false,
                protocolo: lote.protocolo,
                pre_separacao_id: lote.pre_separacao_id,
                lote_id: lote.lote_id
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




// Disponibilizar globalmente
window.PreSeparacaoManager = PreSeparacaoManager;

// Inicializar instância global para funções standalone (sem workspace)
document.addEventListener('DOMContentLoaded', function() {
    if (!window.preSeparacaoManagerGlobal) {
        window.preSeparacaoManagerGlobal = new PreSeparacaoManager(null);
        console.log('✅ Pré-Separação Manager Global inicializado');
    }
});