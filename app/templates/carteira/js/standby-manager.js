/**
 * Gerenciador de Standby
 * Controla as operações de standby de pedidos
 */

window.standbyManager = (function() {
    'use strict';

    let pedidoAtual = null;
    let modal = null;

    /**
     * Inicializa o módulo
     */
    function init() {
        console.log('[StandbyManager] Inicializando...');
        modal = new bootstrap.Modal(document.getElementById('modalStandby'));
        
        // Verificar status de standby de todos os pedidos ao carregar
        verificarStatusTodosPedidos();
    }

    /**
     * Verifica o status de standby de todos os pedidos visíveis
     */
    async function verificarStatusTodosPedidos() {
        const botoes = document.querySelectorAll('.btn-standby');
        
        for (const botao of botoes) {
            const numPedido = botao.dataset.pedido;
            await verificarStatusPedido(numPedido);
        }
    }

    /**
     * Verifica o status de standby de um pedido específico
     */
    async function verificarStatusPedido(numPedido) {
        try {
            const response = await fetch(`/carteira/api/carteira/standby/status/${numPedido}`);
            const data = await response.json();
            
            if (data.success && data.em_standby) {
                atualizarBotaoStandby(numPedido, data.status_standby);
            }
        } catch (error) {
            console.error('[StandbyManager] Erro ao verificar status:', error);
        }
    }

    /**
     * Atualiza a aparência do botão de standby
     */
    function atualizarBotaoStandby(numPedido, statusStandby) {
        const botao = document.getElementById(`btn-standby-${numPedido}`);
        if (!botao) return;
        
        const textSpan = botao.querySelector('.btn-standby-text');
        
        if (statusStandby === 'CONFIRMADO') {
            botao.classList.remove('btn-warning');
            botao.classList.add('confirmado');
            textSpan.textContent = 'Confirmado';
            botao.title = 'Pedido confirmado em standby';
        } else {
            botao.classList.add('btn-warning');
            botao.classList.remove('confirmado');
            textSpan.textContent = 'Em Standby';
            botao.title = `Status: ${statusStandby}`;
        }
    }

    /**
     * Gerencia o standby de um pedido
     */
    window.gerenciarStandby = async function(numPedido) {
        pedidoAtual = numPedido;
        
        // Verificar se já está em standby
        try {
            const response = await fetch(`/carteira/api/carteira/standby/status/${numPedido}`);
            const data = await response.json();
            
            if (data.success && data.em_standby) {
                showAlert('info', `Pedido já está em standby com status: ${data.status_standby}`);
                return;
            }
        } catch (error) {
            console.error('[StandbyManager] Erro ao verificar status:', error);
        }
        
        // Carregar informações do pedido
        await carregarDadosPedido(numPedido);
        
        // Abrir modal
        modal.show();
    };

    /**
     * Carrega os dados do pedido para o modal
     */
    async function carregarDadosPedido(numPedido) {
        const loading = document.getElementById('modal-standby-loading');
        const content = document.getElementById('modal-standby-content');
        
        loading.style.display = 'block';
        content.style.display = 'none';
        
        try {
            // Buscar detalhes do pedido
            const response = await fetch(`/carteira/api/detalhes-pedido/${numPedido}`);
            const data = await response.json();
            
            if (data.success && data.pedido) {
                // Preencher informações do pedido
                document.getElementById('standby-pedido-numero').textContent = numPedido;
                document.getElementById('standby-valor-total').textContent = formatarMoeda(data.pedido.valor_total || 0);
                document.getElementById('standby-peso-total').textContent = `${formatarNumero(data.pedido.peso_total || 0, 2)} kg`;
                document.getElementById('standby-pallet-total').textContent = formatarNumero(data.pedido.pallet_total || 0, 2);
                document.getElementById('standby-data-pedido').textContent = data.pedido.data_pedido || '-';
                
                // Preencher lista de produtos
                const tbody = document.getElementById('standby-produtos-lista');
                tbody.innerHTML = '';
                
                if (data.produtos && data.produtos.length > 0) {
                    data.produtos.forEach(produto => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${produto.cod_produto}</td>
                            <td>${produto.nome_produto}</td>
                            <td class="text-end">${formatarNumero(produto.qtd_saldo_produto_pedido, 3)}</td>
                            <td class="text-end">${formatarMoeda(produto.valor_total || 0)}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
                
                // Limpar seleção de tipo
                document.getElementById('standby-tipo').value = '';
                
                loading.style.display = 'none';
                content.style.display = 'block';
            } else {
                throw new Error('Falha ao carregar dados do pedido');
            }
        } catch (error) {
            console.error('[StandbyManager] Erro ao carregar pedido:', error);
            loading.style.display = 'none';
            content.style.display = 'block';
            showAlert('error', 'Erro ao carregar informações do pedido');
        }
    }

    /**
     * Confirma o envio para standby
     */
    window.confirmarStandby = async function() {
        const tipoStandby = document.getElementById('standby-tipo').value;
        
        if (!tipoStandby) {
            showAlert('warning', 'Selecione o tipo de standby');
            return;
        }
        
        try {
            const response = await fetch('/carteira/api/carteira/standby/criar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    num_pedido: pedidoAtual,
                    tipo_standby: tipoStandby
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showAlert('success', data.message);
                modal.hide();
                
                // Atualizar botão
                atualizarBotaoStandby(pedidoAtual, 'ATIVO');
                
                // Recarregar a página após 2 segundos
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                showAlert('error', data.message || 'Erro ao enviar para standby');
            }
        } catch (error) {
            console.error('[StandbyManager] Erro ao confirmar standby:', error);
            showAlert('error', 'Erro ao processar solicitação');
        }
    };

    /**
     * Formata número para moeda brasileira
     */
    function formatarMoeda(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    /**
     * Formata número com casas decimais
     */
    function formatarNumero(valor, decimais = 2) {
        return parseFloat(valor).toFixed(decimais);
    }

    /**
     * Exibe alertas na tela
     */
    function showAlert(type, message) {
        const alertTypes = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        };
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert ${alertTypes[type]} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    // Retornar API pública
    return {
        init: init,
        verificarStatusPedido: verificarStatusPedido
    };
})();

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    standbyManager.init();
});