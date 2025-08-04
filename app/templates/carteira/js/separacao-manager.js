/**
 * 🎯 SEPARAÇÃO MANAGER
 * Gerencia criação e transformação de separações DEFINITIVAS
 * Para pré-separações, usar pre-separacao-manager.js
 */

class SeparacaoManager {
    constructor() {
        this.init();
    }

    init() {
        console.log('✅ Separação Manager inicializado');
    }

    /**
     * 🎯 CRIAR NOVA SEPARAÇÃO COMPLETA
     * CASO 1: Usado pelos botões principais na carteira agrupada
     * Verifica se tem 1 pré-separação com tipo_envio completo, se tiver transforma em separação
     * Se não tiver pré-separação, solicita a data de expedição e cria uma separação direto
     * Se tiver pré-separação parcial não deixa criar por esse botão
     */
    async criarSeparacaoCompleta(numPedido) {
        console.log(`📦 CASO 1: Criar separação completa para pedido ${numPedido}`);
        
        try {
            // Verificar se já existe lote completo com expedição
            const verificacaoResponse = await fetch(`/carteira/api/pedido/${numPedido}/verificar-lote`);
            
            if (!verificacaoResponse.ok) {
                // Se não existe API de verificação, solicitar data de expedição diretamente
                await this.solicitarDataExpedicaoParaSeparacao(numPedido);
                return;
            }
            
            const verificacaoData = await verificacaoResponse.json();
            
            if (verificacaoData.lote_completo_com_expedicao) {
                // CASO 1a: Lote completo existe, confirmar transformação
                if (confirm(`Existe uma pré-separação completa para este pedido. Deseja transformá-la em separação definitiva?`)) {
                    await this.transformarLoteEmSeparacao(numPedido, verificacaoData.lote_id);
                }
            } else if (verificacaoData.lote_parcial_existe) {
                // CASO 1b: Lote parcial existe, não permitir
                alert('❌ Este pedido possui pré-separação parcial. Não é possível criar separação completa por este botão.');
                return;
            } else {
                // CASO 1c: Não existe lote, solicitar data de expedição
                await this.solicitarDataExpedicaoParaSeparacao(numPedido);
            }
            
        } catch (error) {
            console.error('Erro ao verificar lote:', error);
            // Fallback: solicitar data de expedição diretamente
            await this.solicitarDataExpedicaoParaSeparacao(numPedido);
        }
    }

    /**
     * 🎯 SOLICITAR DATA DE EXPEDIÇÃO E CRIAR SEPARAÇÃO
     */
    async solicitarDataExpedicaoParaSeparacao(numPedido) {
        // Criar modal dinâmico com input de data
        const modalHtml = `
            <div class="modal fade" id="modalDataExpedicao" tabindex="-1">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-calendar me-2"></i>
                                Data de Expedição
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label for="inputDataExpedicao" class="form-label">
                                    Selecione a data de expedição:
                                </label>
                                <input type="date" class="form-control" id="inputDataExpedicao" 
                                       value="${new Date().toISOString().split('T')[0]}" required>
                            </div>
                            <div class="mb-3">
                                <label for="inputAgendamento" class="form-label">
                                    Data de Agendamento (opcional):
                                </label>
                                <input type="date" class="form-control" id="inputAgendamento">
                            </div>
                            <div class="mb-3">
                                <label for="inputProtocolo" class="form-label">
                                    Protocolo (opcional):
                                </label>
                                <input type="text" class="form-control" id="inputProtocolo" 
                                       placeholder="Ex: PROT123">
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Cancelar
                            </button>
                            <button type="button" class="btn btn-primary" id="btnConfirmarExpedicao">
                                <i class="fas fa-check me-1"></i>
                                Confirmar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remover modal se já existir
        const modalExistente = document.getElementById('modalDataExpedicao');
        if (modalExistente) {
            modalExistente.remove();
        }
        
        // Adicionar modal ao body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Criar instância do modal Bootstrap
        const modalElement = document.getElementById('modalDataExpedicao');
        const modal = new bootstrap.Modal(modalElement);
        
        // Configurar handler do botão confirmar
        document.getElementById('btnConfirmarExpedicao').onclick = async () => {
            const dataExpedicao = document.getElementById('inputDataExpedicao').value;
            const agendamento = document.getElementById('inputAgendamento').value;
            const protocolo = document.getElementById('inputProtocolo').value;
            
            if (!dataExpedicao) {
                alert('Por favor, selecione uma data de expedição');
                return;
            }
            
            try {
                // Fechar modal
                modal.hide();
                
                const response = await fetch(`/carteira/api/pedido/${numPedido}/gerar-separacao-completa`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        expedicao: dataExpedicao,
                        agendamento: agendamento || null,
                        protocolo: protocolo || null
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(`Separação criada com sucesso! ${data.separacoes_criadas} produtos separados.`);
                    // Recarregar página para atualizar contadores
                    location.reload();
                } else {
                    alert(`Erro ao criar separação: ${data.error}`);
                }
                
            } catch (error) {
                console.error('Erro ao criar separação:', error);
                alert('Erro interno ao criar separação');
            }
        };
        
        // Limpar modal ao fechar
        modalElement.addEventListener('hidden.bs.modal', function () {
            modalElement.remove();
        });
        
        // Mostrar modal
        modal.show();
    }

    /**
     * 🎯 TRANSFORMAR LOTE EM SEPARAÇÃO
     * CASO 2: Usado dentro do workspace nos lotes existentes
     * Transforma uma pré-separação em separação através de um botão na pré-separação
     */
    async transformarLoteEmSeparacao(numPedido, loteId) {
        console.log(`🔄 CASO 2: Transformar lote ${loteId} em separação`);
        
        try {
            const response = await fetch(`/carteira/api/lote/${loteId}/transformar-separacao`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert(`✅ Lote transformado em separação com sucesso!\n${data.separacoes_criadas} produtos processados.`);
                // Recarregar página para atualizar contadores
                location.reload();
            } else {
                alert(`❌ Erro ao transformar lote: ${data.error}`);
            }
            
        } catch (error) {
            console.error('Erro ao transformar lote:', error);
            alert('❌ Erro interno ao transformar lote em separação');
        }
    }

    /**
     * 🎯 CONFIRMAR TRANSFORMAÇÃO DE LOTE
     * Modal de confirmação para transformar lote específico
     */
    async confirmarTransformacaoLote(loteId) {
        if (confirm(`Deseja transformar o lote ${loteId} em separação?`)) {
            await this.transformarLoteEmSeparacao(null, loteId);
        }
    }

    /**
     * 🎯 REMOVER SEPARAÇÕES INVÁLIDAS
     * Remove qualquer separação que não faça parte dos 3 casos válidos
     */
    async removerSeparacoesInvalidas() {
        console.log('🧹 Verificando separações inválidas...');
        
        // Esta função seria implementada para limpar separações que não seguem os 3 casos
        // Por enquanto, apenas log para não afetar o sistema em produção
        console.log('⚠️ Função de limpeza não implementada - usar com cuidado em produção');
    }
}

// 🎯 FUNÇÕES GLOBAIS PARA ONCLICK
function criarSeparacao(numPedido) {
    if (window.separacaoManager) {
        window.separacaoManager.criarSeparacaoCompleta(numPedido);
    } else {
        console.error('❌ Separação Manager não inicializado');
    }
}

function transformarLote(loteId) {
    if (window.separacaoManager) {
        window.separacaoManager.confirmarTransformacaoLote(loteId);
    } else {
        console.error('❌ Separação Manager não inicializado');
    }
}


// Disponibilizar globalmente
window.SeparacaoManager = SeparacaoManager;

// Inicializar instância global
document.addEventListener('DOMContentLoaded', function() {
    if (!window.separacaoManager) {
        window.separacaoManager = new SeparacaoManager();
        console.log('✅ Separação Manager Global inicializado');
    }
});