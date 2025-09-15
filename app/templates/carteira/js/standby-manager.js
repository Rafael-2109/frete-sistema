/**
 * Gerenciador de Standby
 * Controla as operações de standby de pedidos
 */

window.standbyManager = (function () {
    'use strict';

    let pedidoAtual = null;
    let modal = null;

    /**
     * Inicializa o módulo
     */
    function init() {
        // console.debug('[StandbyManager] Inicializando...');
        modal = new bootstrap.Modal(document.getElementById('modalStandby'));

        // Evitar varredura automática que polui logs: só consulta sob demanda
    }

    /**
     * Verifica o status de standby de todos os pedidos visíveis
     */
    async function verificarStatusTodosPedidos() {
        const botoes = document.querySelectorAll('.btn-standby');
        const pedidos = Array.from(botoes).map(b => b.dataset.pedido).filter(Boolean);
        // Evitar tempestade de requisições: consultar no máximo 10 por segundo
        for (let i = 0; i < pedidos.length; i += 10) {
            const slice = pedidos.slice(i, i + 10);
            await Promise.all(slice.map(p => verificarStatusPedido(p)));
            // Pequeno intervalo para não poluir logs/back-end
            await new Promise(r => setTimeout(r, 200));
        }
    }

    /**
     * Verifica o status de standby de um pedido específico
     */
    async function verificarStatusPedido(numPedido) {
        try {
            const response = await fetch(`/carteira/api/standby/status/${numPedido}`);
            const data = await response.json();

            if (data.success && data.em_standby) {
                atualizarBotaoStandby(numPedido, data.status_standby);
            }
        } catch (error) {
            // console.debug('[StandbyManager] Erro ao verificar status:', error);
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
    window.gerenciarStandby = async function (numPedido) {
        pedidoAtual = numPedido;

        // Verificar se já está em standby
        try {
            const response = await fetch(`/carteira/api/standby/status/${numPedido}`);
            const data = await response.json();

            if (data.success && data.em_standby) {
                showAlert('info', `Pedido já está em standby com status: ${data.status_standby}`);
                return;
            }
        } catch (error) {
            // console.debug('[StandbyManager] Erro ao verificar status:', error);
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
            // Buscar detalhes do pedido usando a rota consolidada atual
            const response = await fetch(`/carteira/api/pedido/${numPedido}/detalhes`);
            const data = await response.json();

            if (data.success) {
                // Preencher informações do pedido (totais vêm em data.totais)
                document.getElementById('standby-pedido-numero').textContent = numPedido;
                const totalValor = (data.totais && typeof data.totais.valor === 'number') ? data.totais.valor : 0;
                const totalPeso = (data.totais && typeof data.totais.peso === 'number') ? data.totais.peso : 0;
                document.getElementById('standby-valor-total').textContent = formatarMoeda(totalValor);
                document.getElementById('standby-peso-total').textContent = `${formatarNumero(totalPeso, 2)} kg`;
                const totalPallet = (data.totais && typeof data.totais.pallet === 'number') ? data.totais.pallet : 0;
                document.getElementById('standby-pallet-total').textContent = formatarNumero(totalPallet, 2);
                document.getElementById('standby-data-pedido').textContent = data.data_pedido || '-';

                // Preencher lista de produtos (itens vêm em data.itens)
                const tbody = document.getElementById('standby-produtos-lista');
                tbody.innerHTML = '';
                (data.itens || []).forEach((produto) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${produto.cod_produto}</td>
                        <td>${produto.nome_produto}</td>
                        <td class="text-end">${formatarNumero(produto.qtd_saldo, 3)}</td>
                        <td class="text-end">${formatarMoeda(produto.valor_total || 0)}</td>
                    `;
                    tbody.appendChild(tr);
                });

                // Limpar seleção de tipo
                document.getElementById('standby-tipo').value = '';

                loading.style.display = 'none';
                content.style.display = 'block';
            } else {
                throw new Error('Falha ao carregar dados do pedido');
            }
        } catch (error) {
            // console.debug('[StandbyManager] Erro ao carregar pedido:', error);
            loading.style.display = 'none';
            content.style.display = 'block';
            showAlert('error', 'Erro ao carregar informações do pedido');
        }
    }

    /**
     * Confirma o envio para standby
     */
    window.confirmarStandby = async function () {
        const tipoStandby = document.getElementById('standby-tipo').value;

        if (!tipoStandby) {
            showAlert('warning', 'Selecione o tipo de standby');
            return;
        }

        try {
            const response = await fetch('/carteira/api/standby/criar', {
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
                // Fechar modal
                modal.hide();

                // Mostrar toast de sucesso
                showToast('success', `Pedido ${pedidoAtual} enviado para standby com sucesso!`);

                // Remover o pedido da interface visualmente
                removerPedidoDaInterface(pedidoAtual);

                // Atualizar contadores se existirem
                atualizarContadores();
            } else {
                showAlert('error', data.message || 'Erro ao enviar para standby');
            }
        } catch (error) {
            // console.debug('[StandbyManager] Erro ao confirmar standby:', error);
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
     * Remove o pedido da interface visualmente
     */
    function removerPedidoDaInterface(numPedido) {
        // Procurar o card/linha do pedido na interface
        // Pode estar em um card (agrupados_balanceado.html) ou em uma linha de tabela

        // Tentar remover card
        const card = document.querySelector(`[data-pedido="${numPedido}"]`);
        if (card) {
            // Adicionar animação de fade out
            card.style.transition = 'opacity 0.5s, transform 0.3s';
            card.style.opacity = '0';
            card.style.transform = 'scale(0.95)';

            setTimeout(() => {
                card.remove();
            }, 500);
        }

        // Tentar remover linha da tabela (se houver)
        const linha = document.querySelector(`tr[data-pedido="${numPedido}"]`);
        if (linha) {
            linha.style.transition = 'opacity 0.5s';
            linha.style.opacity = '0';

            setTimeout(() => {
                linha.remove();
            }, 500);
        }

        // Procurar por elementos com ID específico do pedido
        const elementos = document.querySelectorAll(`[id*="${numPedido}"]`);
        elementos.forEach(el => {
            // Verificar se é um elemento relacionado ao pedido
            if (el.closest('.card') || el.closest('tr')) {
                const container = el.closest('.card') || el.closest('tr');
                if (!container.classList.contains('removing')) {
                    container.classList.add('removing');
                    container.style.transition = 'opacity 0.5s';
                    container.style.opacity = '0';

                    setTimeout(() => {
                        container.remove();
                    }, 500);
                }
            }
        });
    }

    /**
     * Atualiza contadores na interface
     */
    function atualizarContadores() {
        // Atualizar contador de pedidos se existir
        const contadorPedidos = document.querySelector('.contador-pedidos');
        if (contadorPedidos) {
            const valorAtual = parseInt(contadorPedidos.textContent) || 0;
            if (valorAtual > 0) {
                contadorPedidos.textContent = valorAtual - 1;
            }
        }

        // Atualizar outros contadores relevantes
        const totalCards = document.querySelectorAll('.card[data-pedido]').length;
        const contadorGeral = document.querySelector('#total-pedidos');
        if (contadorGeral) {
            contadorGeral.textContent = totalCards;
        }
    }

    /**
     * Exibe toast de notificação (mais elegante que alert)
     */
    function showToast(type, message) {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();

        const toastTypes = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        };

        const toastDiv = document.createElement('div');
        toastDiv.className = `toast align-items-center text-white ${toastTypes[type]} border-0`;
        toastDiv.setAttribute('role', 'alert');
        toastDiv.setAttribute('aria-live', 'assertive');
        toastDiv.setAttribute('aria-atomic', 'true');
        toastDiv.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        toastContainer.appendChild(toastDiv);

        // Inicializar e mostrar o toast
        const toast = new bootstrap.Toast(toastDiv, {
            autohide: true,
            delay: 5000
        });
        toast.show();

        // Remover após ocultar
        toastDiv.addEventListener('hidden.bs.toast', () => {
            toastDiv.remove();
        });
    }

    /**
     * Cria container para toasts se não existir
     */
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }

    /**
     * Exibe alertas na tela (mantido para compatibilidade)
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
document.addEventListener('DOMContentLoaded', function () {
    standbyManager.init();
});